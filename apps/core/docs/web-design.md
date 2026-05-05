# Web Design Settings

Access **Settings > Web Design Settings** to customize the platform appearance.

The settings are organized into tabs for easy navigation.

## Fonts Tab

### Custom Fonts

Add fonts from services like [fonts.bunny.net](https://fonts.bunny.net) or Google Fonts.

For each font, provide:

| Field | Description | Example |
|-------|-------------|---------|
| **Link** | The CSS URL | `https://fonts.bunny.net/css?family=abeezee:400` |
| **Font Family** | The CSS value | `'ABeeZee', sans-serif` |
| **Label** | Display name for the font picker | `ABeeZee` |

### Root Font Assignments

Set the default fonts for:

- **Heading Font** - Used for h1-h6 headings
- **Subheading Font** - Used for secondary headings
- **Body Font** - Used for paragraph text

Default values:
```
Heading: "Handjet", monospace
Subheading: "Roboto", sans-serif
Body: "Open Dyslexic", sans-serif
```

## Colors Tab

### Base Colors

- **White** - Background color (default: `hsl(0, 0%, 100%)`)
- **Black** - Text color (default: `hsl(0, 100%, 0.78%)`)

### Safe Accent Colors (WCAG Compliant)

These colors are designed to meet WCAG contrast requirements:

- **Safe Light Accent** - Light variant that passes contrast
- **Safe Dark Accent** - Dark variant that passes contrast
- **Safe Inverse Accent** - For use on colored backgrounds
- **Safe Inverse Light Accent** - Light inverse variant
- **Safe Inverse Dark Accent** - Dark inverse variant

### Brand Accent Colors

- **Accent** - Primary brand color
- **Light Accent** - Lighter variant
- **Dark Accent** - Darker variant

### Custom Colors

Add additional colors to the palette for use in blocks and components.

## Branding Tab

### Logo

Upload your site logo. Recommended formats:

- SVG (preferred for scalability)
- PNG with transparency

### Favicon

Upload a favicon for browser tabs. Recommended:

- 32x32 or 64x64 PNG

## Pages Tab

Customize text, labels, and colors for programmatic (non-Wagtail) pages:

- Create Session
- Edit Session
- View Session
- Sessions Index
- Manage Availability
- Request Session
- Payment History
- Payment Success

For each page you can customize:

- Heading text and color
- Button text and colors
- Background color

## Back Button Tab

Configure the global back button that appears on all pages:

- **Show Back Button** - Toggle visibility
- **Text** - Button text (default: "Back")
- **Position** - Top left, top right, or top center
- **Font** - Custom font (leave blank for body font)
- **Colors** - Text and background colors
- **Show Icon** - Toggle arrow icon

## Links Tab

Style link hover states globally:

- **Hover Color** - Color when hovering over links
- **Hover Underline** - Show underline on hover
- **Hover Opacity** - Transparency on hover (0-1)
- **Transition Duration** - Animation speed (None, Fast, Normal, Slow)
