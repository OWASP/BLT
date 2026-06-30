use std::time::Duration;

#[derive(Clone, Debug, Default)]
pub struct SecurityHealth {
    pub open_backdoor_ports: Vec<u16>,
    pub world_writable_paths: Vec<String>,
    pub scan_complete: bool,
}

pub async fn run_scan() -> SecurityHealth {
    let mut health = SecurityHealth::default();
    
    // 1. Check backdoor ports
    let backdoor_ports = [31337, 4444, 666, 1337];
    for port in backdoor_ports {
        let addr = format!("127.0.0.1:{}", port);
        // Quick connection attempt
        if tokio::time::timeout(Duration::from_millis(50), tokio::net::TcpStream::connect(&addr)).await.is_ok() {
            health.open_backdoor_ports.push(port);
        }
    }
    
    // 2. Check dangerous permissions
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let paths_to_check = ["/tmp", "/var/tmp"];
        for path in paths_to_check {
            if let Ok(meta) = std::fs::metadata(path) {
                let mode = meta.permissions().mode();
                // Check if other write bit is set
                if mode & 0o002 != 0 {
                    health.world_writable_paths.push(path.to_string());
                }
            }
        }
    }
    
    #[cfg(windows)]
    {
        // Simple stub for Windows
        let paths_to_check = ["C:\\Temp"];
        for path in paths_to_check {
            if let Ok(meta) = std::fs::metadata(path) {
                if !meta.permissions().readonly() {
                    health.world_writable_paths.push(path.to_string());
                }
            }
        }
    }

    health.scan_complete = true;
    health
}
