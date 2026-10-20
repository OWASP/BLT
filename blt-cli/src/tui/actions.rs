//! Asynchronous Background Task Handlers and MCP Tool Dispatchers.
//!
//! This module coordinates non-blocking background workers spawned via `tokio::spawn`
//! to ensure that long-running network requests, MCP tool calls, AI vision analyses,
//! and bulk triage operations never freeze the TUI event loop.
//!
//! Key Functions:
//! - `handle_vision_draft(app, context)`: Initiates Vision AI parsing on a captured image screenshot.
//! - `submit_issue_action(app)`: Packages the vulnerability form and dispatches it to either MCP or REST API.
//! - `bulk_triage_action(app)`: Iterates through selected issues and applies target status updates.
//! - `ai_triage_action(app)`: Prompts the MCP AI agent for automated vulnerability triage recommendations.
//! - `extract_clipboard_action(app)`: Extracts image bytes or file paths across platforms (Windows / Linux / macOS).

use crate::app::{App, RunMode};
use crate::mcp_client::McpSubprocessClient;
use std::sync::Arc;
use tokio::sync::Mutex;

/// Initiates Vision AI parsing on a captured screenshot image with optional context hints.
pub fn handle_vision_draft(app: &mut App, context: Option<String>) {
    app.active_overlay = crate::app::ActiveOverlay::None;
    let path = app.vision_image_path.clone();

    // Preserve existing form data if user was already typing
    if app.submit_form.screenshot_path.is_empty() {
        app.submit_form.screenshot_path = path.clone();
    }
    if app.submit_form.url.is_empty() {
        app.submit_form.url = app.api_base.clone();
    }
    if app.submit_form.description.is_empty() {
        app.submit_form.description = crate::app::VISION_ANALYZING_PLACEHOLDER.to_string();
    }
    app.active_overlay = crate::app::ActiveOverlay::SubmitForm;

    let mcp_client_clone = app.mcp_client.clone();
    let sender = app.event_sender.clone();

    tokio::spawn(async move {
        if let Some(mcp) = mcp_client_clone {
            let mut client_guard = mcp.lock().await;
            let mut payload = serde_json::Map::new();
            payload.insert(
                "image_path".to_string(),
                serde_json::Value::String(path.clone()),
            );
            if let Some(ctx) = context {
                if !ctx.is_empty() {
                    payload.insert("context".to_string(), serde_json::Value::String(ctx));
                }
            }

            match client_guard
                .call_tool("draft_vision_issue", serde_json::Value::Object(payload))
                .await
            {
                Ok(res) => {
                    let (success, content_str) = if let Some(result) = res.get("result") {
                        let is_err = result
                            .get("isError")
                            .and_then(|e| e.as_bool())
                            .unwrap_or(false);
                        let text = result
                            .get("content")
                            .and_then(|c| c.as_array())
                            .and_then(|c| c.first())
                            .and_then(|c| c.get("text"))
                            .and_then(|t| t.as_str())
                            .unwrap_or("No response from Vision AI")
                            .to_string();
                        (!is_err, text)
                    } else {
                        (false, "ERROR: Invalid response structure".to_string())
                    };

                    // Clean up temporary clipboard image file once consumed
                    if path.contains(".blt-mcp") && path.contains("clipboard_") {
                        let _ = std::fs::remove_file(&path);
                    }

                    let _ = sender.send(crate::app::AppEvent::VisionDraftComplete {
                        result: content_str,
                        success,
                    });
                }
                Err(e) => {
                    let err_msg = format!("ERROR: {}", e);
                    // Clean up temporary clipboard image file on failure as well
                    if path.contains(".blt-mcp") && path.contains("clipboard_") {
                        let _ = std::fs::remove_file(&path);
                    }

                    let _ = sender.send(crate::app::AppEvent::VisionDraftComplete {
                        result: err_msg,
                        success: false,
                    });
                }
            }
        } else {
            // Clean up temporary clipboard image file if MCP is unavailable
            if path.contains(".blt-mcp") && path.contains("clipboard_") {
                let _ = std::fs::remove_file(&path);
            }

            let _ = sender.send(crate::app::AppEvent::VisionDraftComplete {
                result: "ERROR: Vision AI requires an active Live MCP connection.".to_string(),
                success: false,
            });
        }
    });
}

/// Dispatches the vulnerability submission form to MCP or REST API.
pub fn submit_issue_action(app: &mut App) {
    if app.submit_form.description == crate::app::VISION_ANALYZING_PLACEHOLDER {
        app.status_message =
            "Notice: Please wait for Vision AI analysis to complete before submitting.".to_string();
        return;
    }

    if let Some(field) = app.submit_form.first_missing_required_field() {
        app.submit_form.active_field = field;
        app.active_overlay = crate::app::ActiveOverlay::SubmitForm;
        app.status_message = "Error: Title, URL, and Description are required.".to_string();
        return;
    }

    app.active_overlay = crate::app::ActiveOverlay::None;
    let title = app.submit_form.title.clone();
    let url = app.submit_form.url.clone();
    let severity = app.submit_form.severity.clone();
    let bug_type = app.submit_form.bug_type.clone();
    let mut desc = app.submit_form.description.clone();
    let steps = app.submit_form.steps_to_reproduce.clone();
    let screenshot = app.submit_form.screenshot_path.clone();

    if app.run_mode == RunMode::Mcp {
        desc = format!("*Submitted by AI Agent via BLT-MCP*\n\n{}", desc);
        if !screenshot.is_empty() {
            desc = format!("{}\n\n[Note: Screenshot '{}' was not included \u{2014} MCP submissions do not support screenshot uploads.]", desc, screenshot);
        }
    }

    let api_base = app.api_base.clone();
    let run_mode = app.run_mode.clone();
    let sender = app.event_sender.clone();
    let mcp_client_clone = app.mcp_client.clone();

    app.status_message = "Submitting vulnerability...".to_string();
    tokio::spawn(async move {
        let is_mcp = run_mode == RunMode::Mcp;

        let (success, message) = if is_mcp {
            if mcp_client_clone.is_none() {
                (
                    false,
                    "ERROR: MCP connection is unavailable. Submission failed.".to_string(),
                )
            } else {
                let mcp = mcp_client_clone.clone().unwrap();
                let mut client_guard = mcp.lock().await;
                let mut payload = serde_json::Map::new();
                payload.insert("url".to_string(), serde_json::Value::String(url.clone()));
                payload.insert(
                    "title".to_string(),
                    serde_json::Value::String(title.clone()),
                );
                payload.insert(
                    "description".to_string(),
                    serde_json::Value::String(desc.clone()),
                );
                payload.insert(
                    "severity".to_string(),
                    serde_json::Value::String(severity.clone()),
                );
                payload.insert(
                    "bug_type".to_string(),
                    serde_json::Value::String(bug_type.clone()),
                );
                payload.insert(
                    "steps_to_reproduce".to_string(),
                    serde_json::Value::String(steps.clone()),
                );
                payload.insert("confirmed".to_string(), serde_json::Value::Bool(true));
                let args = serde_json::Value::Object(payload);

                match client_guard.call_tool("submit_issue", args).await {
                    Ok(res) => {
                        if let Some(result) = res.get("result") {
                            let is_error = result
                                .get("isError")
                                .and_then(|e| e.as_bool())
                                .unwrap_or(false);
                            let content_str = result
                                .get("content")
                                .and_then(|c| c.as_array())
                                .and_then(|c| c.first())
                                .and_then(|c| c.get("text"))
                                .and_then(|t| t.as_str())
                                .unwrap_or("Unknown response from MCP");
                            if is_error {
                                (
                                    false,
                                    format!("ERROR: MCP tool execution failed: {}", content_str),
                                )
                            } else {
                                (true, content_str.to_string())
                            }
                        } else {
                            (
                                false,
                                "ERROR: Invalid response structure from MCP server".to_string(),
                            )
                        }
                    }
                    Err(e) => (
                        false,
                        format!("ERROR: Failed to communicate with MCP: {}", e),
                    ),
                }
            }
        } else {
            match crate::api::submit_issue(
                &api_base,
                &url,
                &title,
                &severity,
                &bug_type,
                &desc,
                &steps,
                &screenshot,
            )
            .await
            {
                Ok(_) => (true, "SUCCESS: Vulnerability report submitted!".to_string()),
                Err(e) => (false, format!("ERROR: Failed to submit: {}", e)),
            }
        };

        let _ = sender.send(crate::app::AppEvent::SubmitResult { success, message });

        // Background refresh: wait a moment then re-fetch the live issues list
        if success {
            tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;
            if is_mcp {
                if let Some(mcp) = mcp_client_clone {
                    let mut client_guard = mcp.lock().await;
                    if let Ok(resp) = client_guard.read_resource("blt://v2/bugs").await {
                        if let Some(contents) = resp
                            .get("result")
                            .and_then(|r| r.get("contents"))
                            .and_then(|c| c.as_array())
                            .and_then(|c| c.first())
                            .and_then(|c| c.get("text"))
                            .and_then(|t| t.as_str())
                        {
                            if let Ok(root) = serde_json::from_str::<serde_json::Value>(contents) {
                                if let Ok(fresh_issues) = crate::api::parse_issues_from_json(&root)
                                {
                                    let total = fresh_issues.len() as u32;
                                    let _ = sender.send(crate::app::AppEvent::IssuesRefreshed {
                                        issues: fresh_issues,
                                        total,
                                    });
                                }
                            }
                        }
                    }
                }
            } else if let Ok(fresh_issues) = crate::api::get_issues(&api_base).await {
                let total = fresh_issues.len() as u32;
                let _ = sender.send(crate::app::AppEvent::IssuesRefreshed {
                    issues: fresh_issues,
                    total,
                });
            }
        }
    });
}

/// Spawns asynchronous bulk triage execution over multiple selected issue IDs.
pub fn bulk_triage_action(app: &mut App) {
    app.active_overlay = crate::app::ActiveOverlay::None;
    let target = app.triage_target_status.clone();
    let count = app.selected_issues.len();
    app.status_message = format!("Bulk triaging {} issues to '{}'...", count, target);
    let sender = app.event_sender.clone();
    let issue_ids: Vec<String> = app.selected_issues.iter().cloned().collect();
    let mcp_client_clone = app.mcp_client.clone();
    let api_base = app.api_base.clone();

    tokio::spawn(async move {
        let mut all_succeeded = true;
        let mut failed_count = 0;
        let mut first_error = String::new();

        for id in &issue_ids {
            let res = if let Some(ref client_mutex) = mcp_client_clone {
                let mut client = client_mutex.lock().await;
                let args = serde_json::json!({
                    "id": id,
                    "status": target,
                    "confirmed": true
                });
                client.call_tool("update_bug", args).await.map(|_| ())
            } else {
                crate::api::submit_issue_triage(&api_base, id, &target).await
            };

            let (success, message) = match res {
                Ok(_) => (
                    true,
                    format!(
                        "Bulk triage: successfully updated status for #{} to {}",
                        id, target
                    ),
                ),
                Err(e) => {
                    all_succeeded = false;
                    failed_count += 1;
                    if first_error.is_empty() {
                        first_error = e.to_string();
                    }
                    (
                        false,
                        format!("Bulk triage: failed to update status for #{}: {}", id, e),
                    )
                }
            };

            let _ = sender.send(crate::app::AppEvent::TriageConfirmed {
                issue_id: id.clone(),
                success,
                message,
                target_status: target.clone(),
            });
        }

        if all_succeeded {
            let _ = sender.send(crate::app::AppEvent::SubmitResult {
                success: true,
                message: format!(
                    "Successfully bulk triaged {} issues to '{}'.",
                    count, target
                ),
            });
        } else {
            let _ = sender.send(crate::app::AppEvent::SubmitResult {
                success: false,
                message: format!(
                    "Bulk triage completed with errors: {} failed. First error: {}",
                    failed_count, first_error
                ),
            });
        }
    });
}

/// Spawns an asynchronous task to analyze a vulnerability using the MCP AI tool.
pub fn ai_triage_action(
    mcp_opt: Option<Arc<Mutex<McpSubprocessClient>>>,
    sender: tokio::sync::mpsc::UnboundedSender<crate::app::AppEvent>,
    issue_id: String,
    issue_title: String,
    issue_desc: String,
) {
    if let Some(mcp) = mcp_opt {
        tokio::spawn(async move {
            let prompt = format!(
                "Please analyze Issue #{}: {} - {}",
                issue_id, issue_title, issue_desc
            );
            let args = serde_json::json!({
                "prompt": prompt
            });

            let mut client = mcp.lock().await;
            match client.call_tool("triage_vulnerability", args).await {
                Ok(resp) => {
                    let is_err = resp
                        .get("result")
                        .and_then(|r| r.get("isError"))
                        .and_then(|ie| ie.as_bool())
                        .unwrap_or(false);

                    let text = resp
                        .get("result")
                        .and_then(|r| r.get("content"))
                        .and_then(|c| c.as_array())
                        .and_then(|arr| arr.first())
                        .and_then(|first| first.get("text"))
                        .and_then(|t| t.as_str())
                        .unwrap_or("No analysis returned from MCP.");

                    let (success, message) = if is_err {
                        (
                            false,
                            format!("AI Triage Failed for Issue #{}: {}", issue_id, text),
                        )
                    } else {
                        (
                            true,
                            format!("AI Triage Complete for Issue #{}:\n\n{}", issue_id, text),
                        )
                    };
                    let _ = sender.send(crate::app::AppEvent::AiTriageResult { message, success });
                }
                Err(e) => {
                    let message = format!("AI Triage Failed for Issue #{}: {}", issue_id, e);
                    let _ = sender.send(crate::app::AppEvent::AiTriageResult {
                        message,
                        success: false,
                    });
                }
            }
        });
    } else {
        let message = "Error: AI Triage requires an active Live MCP connection.".to_string();
        let _ = sender.send(crate::app::AppEvent::AiTriageResult {
            message,
            success: false,
        });
    }
}

/// Extracts clipboard image data or path string across Windows and Unix platforms.
pub fn extract_clipboard_action(app: &mut App) {
    app.status_message = "Reading image or path from clipboard...".to_string();
    let sender = app.event_sender.clone();

    #[cfg(windows)]
    {
        tokio::spawn(async move {
            let output = tokio::task::spawn_blocking(|| {
                std::process::Command::new("powershell.exe")
                    .args([
                        "-NoProfile",
                        "-Command",
                        "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; if ([System.Windows.Forms.Clipboard]::ContainsImage()) { $img = [System.Windows.Forms.Clipboard]::GetImage(); $temp = [System.IO.Path]::GetTempFileName() + '.png'; $img.Save($temp, [System.Drawing.Imaging.ImageFormat]::Png); Write-Output \"SUCCESS:$temp\"; } else { if ([System.Windows.Forms.Clipboard]::ContainsText()) { $txt = [System.Windows.Forms.Clipboard]::GetText().Trim().Trim('\"'); if (Test-Path $txt -PathType Leaf) { Write-Output \"SUCCESS:$txt\"; } else { Write-Output 'NO_IMAGE'; } } else { Write-Output 'NO_IMAGE'; } }"
                    ])
                    .output()
            })
            .await;

            let result = match output {
                Ok(Ok(out)) => {
                    let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
                    if stdout.starts_with("SUCCESS:") {
                        Ok(stdout["SUCCESS:".len()..].trim().to_string())
                    } else if stdout.contains("NO_IMAGE") {
                        Err("Clipboard does not contain an image or valid image path.".to_string())
                    } else {
                        Err(format!("PowerShell error: {}", stdout))
                    }
                }
                _ => Err("Failed to execute PowerShell command".to_string()),
            };
            let _ = sender.send(crate::app::AppEvent::ClipboardExtracted { result });
        });
    }

    #[cfg(not(windows))]
    {
        tokio::spawn(async move {
            let result = tokio::task::spawn_blocking(move || {
                match arboard::Clipboard::new() {
                    Ok(mut clipboard) => {
                        match clipboard.get_image() {
                            Ok(image) => {
                                let home = dirs::home_dir().unwrap_or_default();
                                let img_dir = home.join(".blt-mcp").join("images");
                                let _ = std::fs::create_dir_all(&img_dir);

                                // Prune stale clipboard files older than 24 hours
                                if let Ok(entries) = std::fs::read_dir(&img_dir) {
                                    let now = std::time::SystemTime::now();
                                    for entry in entries.flatten() {
                                        if let Ok(meta) = entry.metadata() {
                                            if let Ok(modified) = meta.modified() {
                                                if let Ok(age) = now.duration_since(modified) {
                                                    if age.as_secs() > 24 * 3600 {
                                                        let _ = std::fs::remove_file(entry.path());
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                let timestamp = std::time::SystemTime::now()
                                    .duration_since(std::time::UNIX_EPOCH)
                                    .unwrap_or_default()
                                    .as_millis();
                                let temp_path = img_dir.join(format!("clipboard_{}.png", timestamp));

                                let mut png_bytes = Vec::new();
                                let mut encoder = png::Encoder::new(&mut png_bytes, image.width as u32, image.height as u32);
                                encoder.set_color(png::ColorType::Rgba);
                                encoder.set_depth(png::BitDepth::Eight);

                                let mut write_success = false;
                                if let Ok(mut writer) = encoder.write_header() {
                                    if writer.write_image_data(&image.bytes).is_ok() {
                                        write_success = true;
                                    }
                                }

                                if write_success && std::fs::write(&temp_path, &png_bytes).is_ok() {
                                    Ok(temp_path.to_string_lossy().to_string())
                                } else {
                                    Err("Error: Failed to save clipboard image.".to_string())
                                }
                            }
                            Err(_) => {
                                if let Ok(text) = clipboard.get_text() {
                                    let trimmed = text.trim().replace('"', "");
                                    let path_str = if cfg!(target_os = "linux") {
                                         if trimmed.as_bytes().get(1..3) == Some(b":\\") {
                                             let drive = trimmed[0..1].to_lowercase();
                                             let rest = trimmed[3..].replace('\\', "/");
                                             format!("/mnt/{}/{}", drive, rest)
                                         } else {
                                             trimmed
                                         }
                                    } else {
                                        trimmed
                                    };
                                    let p = std::path::Path::new(&path_str);
                                    if p.exists() && p.is_file() {
                                        Ok(path_str)
                                    } else {
                                        Err("Clipboard does not contain an image or valid image path.".to_string())
                                    }
                                } else {
                                    Err("Clipboard does not contain an image.".to_string())
                                }
                            }
                        }
                    }
                    Err(e) => {
                        Err(format!("Error: Clipboard access failed: {}", e))
                    }
                }
            })
            .await;

            let final_res = match result {
                Ok(res) => res,
                Err(_) => Err("Clipboard extraction task panicked".to_string()),
            };
            let _ = sender.send(crate::app::AppEvent::ClipboardExtracted { result: final_res });
        });
    }
}
