# Content Management

Manage site content using Wagtail's page editor and StreamField blocks.

## Page Types

### Home Page

The main landing page with StreamField content. Limited to one per site.

Can contain:
- Hero sections
- Feature grids
- Testimonials
- Call-to-action blocks

### Blog Index Page

Blog listing page with optional blog feed block.

**Important**: To display blog posts, you must add a **Blog Feed Block** to the page body. If no block is added, the page will show "No blogs yet."

### Blog Page

Individual blog posts with:
- Date
- Intro/excerpt
- Body content

### Sessions Index Page

Session browsing and management interface. This is a routable page that serves both CMS content and programmatic routes.

### Contact Form Page

Contact form with customizable fields and topics.

## StreamField Blocks

Available blocks for page building:

### Hero Block

Full-width banner section with:
- Background image
- Heading and subheading
- Call-to-action button
- Minimum height setting
- Background and text colors

### Text Block

Rich text content with:
- Headings (h1-h3)
- Bold, italic, links
- Lists (ordered/unordered)
- Code blocks and blockquotes
- Max width setting

### Styled Rich Text Block

Extended text block with link hover customization:
- Default link color
- Hover color and opacity
- Underline behavior
- Transition effects

### Text + Image Block

Two-column layout with:
- Heading
- Rich text content
- Image
- Image position (left/right)

### Call-to-Action Block

Prominent action section with:
- Heading
- Description
- Button with link
- Button colors

### Testimonial Block

Quote display with:
- Quote text
- Author name and title
- Author image
- Star rating (1-5)

### Feature Grid Block

Grid of feature cards with:
- Section heading
- Up to 6 features
- Each feature has title, description, icon
- Column count (2-4)

### FAQ/Accordion Block

Expandable Q&A section with:
- Section heading
- Multiple FAQ items
- Each item has question and answer

### Spacer Block

Vertical spacing with:
- Height options (Small, Medium, Large, Extra Large)

### Grid Block

Flexible layout grid with:
- Multiple nested blocks
- Column count (2-4)

### Marquee Block

Scrolling text with:
- Content text
- Repeat count
- Size (small/medium/large)
- Speed (slow/medium/fast)

### Blog Feed Block

Display blog posts with:
- Heading
- Max posts to display
- Show/hide date and excerpt
- Empty message customization
- Link styling options

### Back Button Block

Customizable back button with:
- Text
- Link (or browser history)
- Position
- Font and colors
- Icon toggle

## Block Styling Options

Most blocks include common styling options:

### Colors
- Background color
- Text color

### Borders
- Top border (style, color, size)
- Bottom border (style, color, size)

Border styles available:
- None
- Zigzag
- Wave
- Rounded
- Lego Wave
- Left Curve
- Right Curve

### Back Button
Each block can optionally show a back button with:
- Custom text
- Custom link
- Color customization
