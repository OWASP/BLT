# Email Templates

This directory contains HTML email templates for the BLT API.

## Template Files

| File | Purpose | Variables |
|------|---------|-----------|
| `base.html` | Base layout wrapper | `[[title]]`, `[[content]]` |
| `verification.html` | Email verification | `[[username]]`, `[[verification_link]]`, `[[expires_hours]]` |
| `password_reset.html` | Password reset | `[[username]]`, `[[reset_link]]`, `[[expires_hours]]` |
| `welcome.html` | Welcome email | `[[username]]`, `[[dashboard_link]]` |
| `bug_confirmation.html` | Bug submission | `[[username]]`, `[[bug_id]]`, `[[bug_title]]` |

## 🎨 How It Works

1. **Separate HTML from Python** - All HTML is in external `.html` files
2. **Dynamic placeholders** - Use `[[variable_name]]` syntax for dynamic content
3. **Auto-escaping** - All variables are automatically HTML-escaped for security
4. **Template inheritance** - Content templates are wrapped in `base.html` layout
5. **Valid CSS** - CSS uses normal `{}` braces, no conflicts with placeholders

## Usage Example

### Python Code
```python
from services.email_templates import get_verification_email

html = get_verification_email(
    username="john_doe",
    verification_link="https://blt.owasp.org/verify?token=abc123",
    expires_hours=24
)
```

### Template File (`verification.html`)
```html
<p>Hello <strong>[[username]]</strong>,</p>
<a href="[[verification_link]]" class="button">Verify Email</a>
<p>Expires in [[expires_hours]] hours.</p>
```

### Rendered Output
```html
<p>Hello <strong>john_doe</strong>,</p>
<a href="https://blt.owasp.org/verify?token=abc123" class="button">Verify Email</a>
<p>Expires in 24 hours.</p>
```

## ✏️ Editing Templates

1. **Preview changes** - Open `.html` files in browser to preview (CSS works perfectly!)
2. **Edit freely** - No Python knowledge needed to modify templates
3. **Use placeholders** - Add `[[variable_name]]` where you need dynamic content
4. **Keep styling** - All CSS classes are defined in `base.html` with normal `{}` braces

## Security

- **XSS Protection** - All variables are automatically HTML-escaped
- **No code execution** - Templates are pure HTML with safe string replacement
- **Validation** - Missing variables throw clear error messages- **CSS Safe** - Uses `[[var]]` syntax to avoid conflicts with CSS `{}` braces
## Adding New Templates

1. Create new `.html` file in this directory
2. Add placeholders using `[[variable_name]]` syntax (double square brackets)

```python
def get_my_new_email(var1: str, var2: str) -> str:
    """Description of the email."""
    content = load_template(
        'my_new_email.html',
        var1=var1,
        var2=var2
    )
    return render_in_base(content, "Email Title - OWASP BLT")
```

## CSS Classes

Common CSS classes available in templates:

- `.button` - Primary action button (red)
- `.button-wrap` - Center-aligned button container
- `.info-box` - Highlighted info box (red border)
- `.link-box` - Copyable link display
- `.divider` - Horizontal separator line
- `.muted` - Gray secondary text
- `.small` - Smaller text for disclaimers

## Email Best Practices

**Do:**
- Keep content concise and scannable
- Use clear call-to-action buttons
- Include plain text fallback links
- Test on multiple email clients

**Don't:**
- Use JavaScript (not supported in emails)
- Use external CSS files (inline styles only)
- Forget mobile responsiveness
- Include sensitive data in links
