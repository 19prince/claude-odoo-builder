# Odoo Design System Reference

This is the living reference Claude reads before writing any page HTML. Contains Bootstrap/Odoo conventions and paste-ready section templates.

---

## Bootstrap Version by Odoo Release

| Odoo version | Bootstrap version | Notes |
|---|---|---|
| 17.0 | Bootstrap 5.1 | Default. Use BS5 utilities. |
| 16.0 | Bootstrap 5.1 | Same as 17 |
| 15.0 | Bootstrap 4.6 | Avoid BS5-only classes |
| 14.0 and below | Bootstrap 4.5 | Older grid/utility syntax |

**BS5-only utilities to avoid on Odoo 15/14:**
- `gap-*`, `d-grid`, `fs-*` (use `font-size`), `g-*` gutter (use `gutter`), `me-/ms-` (use `mr-/ml-`)

When unsure of the user's version, ask before writing. Default assumption: Odoo 17 (Bootstrap 5).

---

## Odoo-Specific CSS Classes

| Class | Purpose |
|---|---|
| `o_colored_level` | Enables background color picker in editor sidebar. Add to every `<section>`. |
| `o_editable` | Marks a container as user-editable in the WYSIWYG editor. Add to every text block. |
| `o_we_bg_filter` | Adds a color overlay on top of a background image. |
| `o_header_standard` | Standard header layout variant. |
| `s_banner` | Odoo's hero/banner section base class. |
| `s_text_block` | Simple text section. |
| `s_three_columns` | 3-column feature grid. |
| `s_call_to_action` | Call-to-action section. |
| `s_text_image` | Split content (text + image). |
| `s_quotes_carousel` | Testimonials / quotes section. |
| `s_website_form` | Contact/lead capture form section. |
| `s_hr` | Horizontal rule divider section. |

The `s_*` classes are Odoo's built-in snippet identifiers. You can use them on your custom sections — they inherit basic styling from Odoo's stylesheet.

---

## Typography

```html
<!-- Display headings — large, impactful -->
<h1 class="display-1">Massive Title</h1>   <!-- page hero -->
<h2 class="display-4">Section Title</h2>   <!-- section headers -->

<!-- Semantic headings -->
<h2 class="fw-bold">Bold Section Title</h2>
<h3>Subsection</h3>

<!-- Body variants -->
<p class="lead">Larger intro paragraph, typically follows a display heading.</p>
<p class="text-muted">Secondary / supporting text.</p>
<small class="text-muted">Fine print or captions.</small>
```

**Font weights:** `fw-light`, `fw-normal`, `fw-semibold`, `fw-bold`, `fw-bolder`
**Text alignment:** `text-start`, `text-center`, `text-end`
**Italic:** `fst-italic`

---

## Color Utilities

### Background colors
```html
<section class="bg-primary text-white">...</section>
<section class="bg-secondary text-white">...</section>
<section class="bg-light">...</section>
<section class="bg-dark text-white">...</section>
<section class="bg-white">...</section>
```

### Text colors
```html
<p class="text-primary">Brand color text</p>
<p class="text-muted">Subdued text</p>
<p class="text-white">White text (on dark bg)</p>
<p class="text-dark">Dark text</p>
<p class="text-danger">Error / alert text</p>
<p class="text-success">Success / positive text</p>
```

### Odoo theme CSS variables (use in inline styles or custom SCSS)
```css
var(--color-primary)       /* primary brand color */
var(--color-secondary)     /* secondary brand color */
var(--headings-color)      /* heading text color */
var(--body-color)          /* body text color */
var(--headings-font)       /* heading font stack */
var(--body-font)           /* body font stack */
```

---

## Spacing System (Bootstrap 5)

Spacing scale: `1`=4px, `2`=8px, `3`=16px, `4`=24px, `5`=48px

```html
<!-- Padding -->
<section class="py-5">...</section>          <!-- vertical: 48px top + bottom -->
<div class="px-4">...</div>                  <!-- horizontal padding -->
<div class="p-3">...</div>                   <!-- all sides -->
<div class="pt-2 pb-4">...</div>             <!-- top 8px, bottom 24px -->

<!-- Margin -->
<h2 class="mt-3 mb-2">...</h2>
<div class="mx-auto">...</div>               <!-- center block element -->
<div class="ms-auto">...</div>               <!-- push right (BS5) -->
```

**Standard section rhythm:** `py-5` on every `<section>` for consistent vertical spacing.

---

## Grid System

```html
<!-- Standard page-width container -->
<div class="container">...</div>

<!-- Full-width container -->
<div class="container-fluid">...</div>

<!-- Row with gutters -->
<div class="row g-4">                        <!-- g-4 = gap between columns -->
  <div class="col-12 col-md-6 col-lg-4">...</div>
  <div class="col-12 col-md-6 col-lg-4">...</div>
  <div class="col-12 col-md-6 col-lg-4">...</div>
</div>

<!-- Vertically centered row -->
<div class="row align-items-center">...</div>

<!-- Horizontally centered row -->
<div class="row justify-content-center">...</div>
```

Common column patterns:
- 2 equal columns: `col-md-6`
- 3 equal columns: `col-md-4`
- 4 equal columns: `col-md-3`
- 60/40 split: `col-lg-7` + `col-lg-5`
- Sidebar layout: `col-lg-8` + `col-lg-4`

---

## Buttons

```html
<!-- Primary action -->
<a href="#" class="btn btn-primary btn-lg o_editable">Get Started</a>

<!-- Secondary / outline -->
<a href="#" class="btn btn-outline-secondary o_editable">Learn More</a>

<!-- White (on dark backgrounds) -->
<a href="#" class="btn btn-light btn-lg o_editable">Contact Us</a>

<!-- Outline white (on colored backgrounds) -->
<a href="#" class="btn btn-outline-light o_editable">View Demo</a>

<!-- Full-width -->
<a href="#" class="btn btn-primary w-100">Submit</a>
```

Always use `<a>` tags (not `<button>`) for buttons in Odoo page arch — the editor handles them better.

---

## Images

```html
<!-- Always responsive -->
<img src="URL" class="img-fluid" alt="Description">

<!-- Rounded corners -->
<img src="URL" class="img-fluid rounded" alt="">

<!-- Circle (avatars) -->
<img src="URL" class="img-fluid rounded-circle" style="width:80px; height:80px; object-fit:cover;" alt="">

<!-- With shadow -->
<img src="URL" class="img-fluid rounded shadow" alt="">
<img src="URL" class="img-fluid rounded shadow-lg" alt="">
```

Placeholder image URLs (use until real images are provided):
```
https://placehold.co/800x500/EEE/999?text=Hero+Image
https://placehold.co/600x400/DEE/336?text=Feature+Image
https://placehold.co/48x48/CCC/666?text=A       ← avatar
https://placehold.co/400x300/EEF/336?text=Card+Image
```

---

## Cards

```html
<!-- Basic card -->
<div class="card border-0 shadow-sm h-100">
  <div class="card-body p-4">
    <h5 class="card-title o_editable">Card Title</h5>
    <p class="card-text text-muted o_editable">Card body text here.</p>
  </div>
</div>

<!-- Card with image top -->
<div class="card border-0 shadow-sm h-100">
  <img src="URL" class="card-img-top" alt="">
  <div class="card-body p-4">
    <h5 class="card-title o_editable">Title</h5>
    <p class="card-text text-muted o_editable">Description.</p>
    <a href="#" class="btn btn-primary btn-sm o_editable">Read More</a>
  </div>
</div>
```

---

## QWeb Arch Wrapper Format

Every page arch pushed to Odoo must be wrapped in this template (push_page.py does this automatically, but include it if writing arch directly):

```xml
<t t-name="website.page_{url_slug}">
  <t t-call="website.layout">
    <t t-set="pageName" t-value="'Page Name Here'"/>
    <!-- sections go here -->
  </t>
</t>
```

The `t-name` key must be unique. Convention: `website.page_{slug}` where slug is the URL without slashes (e.g., `website.page_about`).

---

## Paste-Ready Section Templates

Copy these blocks directly into page drafts. Customize copy and colors as needed.

---

### HERO — Full-Width with Two CTAs

```html
<section class="s_banner o_colored_level py-5 bg-dark text-white">
  <div class="container py-4">
    <div class="row align-items-center g-5">
      <div class="col-lg-6">
        <p class="text-uppercase fw-semibold text-primary mb-2 o_editable" style="letter-spacing:.1em;">Your Tagline</p>
        <h1 class="display-4 fw-bold o_editable">A Headline That Gets Attention</h1>
        <p class="lead mt-3 text-white-50 o_editable">
          One or two sentences explaining what you offer and who it's for.
          Keep it punchy and benefit-focused.
        </p>
        <div class="mt-4 d-flex flex-wrap gap-3">
          <a href="/contactus" class="btn btn-primary btn-lg o_editable">Get Started</a>
          <a href="#" class="btn btn-outline-light btn-lg o_editable">Watch Demo</a>
        </div>
      </div>
      <div class="col-lg-6 text-center">
        <img
          src="https://placehold.co/600x440/1a1a2e/6c63ff?text=Hero+Image"
          class="img-fluid rounded-3 shadow-lg"
          alt="Hero visual"
        />
      </div>
    </div>
  </div>
</section>
```

---

### FEATURES — Three-Column Icon Grid

```html
<section class="s_three_columns o_colored_level py-5">
  <div class="container">
    <div class="row text-center mb-5">
      <div class="col-12">
        <h2 class="display-6 fw-bold o_editable">Why Choose Us</h2>
        <p class="text-muted mx-auto o_editable" style="max-width:560px;">
          A brief supporting sentence for this features section.
        </p>
      </div>
    </div>
    <div class="row g-4">
      <div class="col-md-4">
        <div class="card border-0 shadow-sm p-4 h-100 text-center">
          <div class="mb-3">
            <span class="display-5 text-primary">&#9733;</span>
          </div>
          <h4 class="fw-semibold o_editable">Feature One</h4>
          <p class="text-muted o_editable">Describe this benefit clearly in two or three short sentences. Focus on outcomes.</p>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card border-0 shadow-sm p-4 h-100 text-center">
          <div class="mb-3">
            <span class="display-5 text-primary">&#9650;</span>
          </div>
          <h4 class="fw-semibold o_editable">Feature Two</h4>
          <p class="text-muted o_editable">Describe this benefit clearly in two or three short sentences. Focus on outcomes.</p>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card border-0 shadow-sm p-4 h-100 text-center">
          <div class="mb-3">
            <span class="display-5 text-primary">&#10003;</span>
          </div>
          <h4 class="fw-semibold o_editable">Feature Three</h4>
          <p class="text-muted o_editable">Describe this benefit clearly in two or three short sentences. Focus on outcomes.</p>
        </div>
      </div>
    </div>
  </div>
</section>
```

---

### SPLIT CONTENT — Image Left, Text Right

```html
<section class="s_text_image o_colored_level py-5">
  <div class="container">
    <div class="row align-items-center g-5">
      <div class="col-lg-5">
        <img
          src="https://placehold.co/540x420/EEF/336?text=Section+Image"
          class="img-fluid rounded-3 shadow"
          alt="Section visual"
        />
      </div>
      <div class="col-lg-7">
        <p class="text-uppercase fw-semibold text-primary mb-2 o_editable" style="letter-spacing:.08em;">Section Label</p>
        <h2 class="fw-bold o_editable">A Compelling Section Headline</h2>
        <p class="lead text-muted mt-3 o_editable">
          Opening paragraph that hooks the reader with the most important point.
        </p>
        <p class="o_editable">
          Supporting detail in a second paragraph. Keep it concise — two or three sentences maximum per paragraph.
        </p>
        <ul class="mt-3 text-muted o_editable">
          <li>Key benefit or feature point one</li>
          <li>Key benefit or feature point two</li>
          <li>Key benefit or feature point three</li>
        </ul>
        <a href="#" class="btn btn-primary mt-4 o_editable">Learn More</a>
      </div>
    </div>
  </div>
</section>
```

---

### SPLIT CONTENT — Text Left, Image Right (flip variant)

```html
<section class="s_text_image o_colored_level py-5 bg-light">
  <div class="container">
    <div class="row align-items-center g-5">
      <div class="col-lg-7">
        <p class="text-uppercase fw-semibold text-primary mb-2 o_editable" style="letter-spacing:.08em;">Another Section</p>
        <h2 class="fw-bold o_editable">Second Section Headline</h2>
        <p class="lead text-muted mt-3 o_editable">Lead paragraph with the main idea.</p>
        <p class="o_editable">Detailed supporting paragraph with additional context.</p>
        <a href="#" class="btn btn-outline-primary mt-4 o_editable">Discover More</a>
      </div>
      <div class="col-lg-5">
        <img
          src="https://placehold.co/540x420/DEE/363?text=Another+Image"
          class="img-fluid rounded-3 shadow"
          alt=""
        />
      </div>
    </div>
  </div>
</section>
```

---

### CALL TO ACTION — Full-Width Centered

```html
<section class="s_call_to_action o_colored_level py-5 bg-primary text-white text-center">
  <div class="container py-3">
    <h2 class="display-6 fw-bold o_editable">Ready to Get Started?</h2>
    <p class="lead mt-3 text-white-50 o_editable" style="max-width:560px; margin:auto;">
      Join hundreds of businesses already using our solution to grow faster.
    </p>
    <div class="mt-5 d-flex flex-wrap justify-content-center gap-3">
      <a href="/contactus" class="btn btn-light btn-lg px-5 o_editable">Talk to Sales</a>
      <a href="#" class="btn btn-outline-light btn-lg px-5 o_editable">Start Free Trial</a>
    </div>
  </div>
</section>
```

---

### TESTIMONIALS — Three-Column Quote Cards

```html
<section class="s_quotes_carousel o_colored_level py-5 bg-light">
  <div class="container">
    <h2 class="text-center fw-bold mb-2 o_editable">What Our Clients Say</h2>
    <p class="text-center text-muted mb-5 o_editable">Real results from real businesses.</p>
    <div class="row g-4">
      <div class="col-md-4">
        <div class="card border-0 shadow-sm p-4 h-100">
          <div class="text-warning mb-3">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
          <p class="fst-italic text-muted o_editable">
            "This solution completely transformed how our team works. Setup was fast,
            support was excellent, and results were immediate."
          </p>
          <div class="mt-auto pt-3 d-flex align-items-center">
            <img
              src="https://placehold.co/48x48/CCC/666?text=A"
              class="rounded-circle me-3"
              style="width:48px;height:48px;object-fit:cover;"
              alt="Avatar"
            />
            <div>
              <strong class="o_editable">Jane Smith</strong>
              <div class="text-muted small o_editable">CEO, Acme Corp</div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card border-0 shadow-sm p-4 h-100">
          <div class="text-warning mb-3">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
          <p class="fst-italic text-muted o_editable">
            "I was skeptical at first, but after seeing the results in the first month,
            I couldn't imagine running our business without it."
          </p>
          <div class="mt-auto pt-3 d-flex align-items-center">
            <img
              src="https://placehold.co/48x48/CCC/666?text=B"
              class="rounded-circle me-3"
              style="width:48px;height:48px;object-fit:cover;"
              alt="Avatar"
            />
            <div>
              <strong class="o_editable">Mark Johnson</strong>
              <div class="text-muted small o_editable">COO, Beta Inc</div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card border-0 shadow-sm p-4 h-100">
          <div class="text-warning mb-3">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
          <p class="fst-italic text-muted o_editable">
            "The team is incredibly responsive and the platform keeps getting better.
            Highly recommend to any growing business."
          </p>
          <div class="mt-auto pt-3 d-flex align-items-center">
            <img
              src="https://placehold.co/48x48/CCC/666?text=C"
              class="rounded-circle me-3"
              style="width:48px;height:48px;object-fit:cover;"
              alt="Avatar"
            />
            <div>
              <strong class="o_editable">Sarah Lee</strong>
              <div class="text-muted small o_editable">Founder, Gamma Co</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>
```

---

### PRICING TABLE — Two-Tier with Highlighted Tier

```html
<section class="s_pricing o_colored_level py-5">
  <div class="container">
    <div class="text-center mb-5">
      <h2 class="fw-bold o_editable">Simple, Transparent Pricing</h2>
      <p class="text-muted o_editable">No hidden fees. Cancel anytime.</p>
    </div>
    <div class="row g-4 justify-content-center">
      <div class="col-md-5 col-lg-4">
        <div class="card border-0 shadow p-4 text-center h-100">
          <h4 class="fw-semibold o_editable">Starter</h4>
          <div class="display-5 fw-bold my-3 o_editable">$49<span class="fs-6 fw-normal text-muted">/mo</span></div>
          <p class="text-muted small o_editable">Perfect for small teams and getting started.</p>
          <ul class="list-unstyled text-start text-muted mt-3 mb-4">
            <li class="mb-2 o_editable"><span class="text-success me-2">&#10003;</span>Up to 5 users</li>
            <li class="mb-2 o_editable"><span class="text-success me-2">&#10003;</span>Core features</li>
            <li class="mb-2 o_editable"><span class="text-success me-2">&#10003;</span>Email support</li>
            <li class="text-muted o_editable"><span class="me-2">&#10007;</span>Advanced analytics</li>
          </ul>
          <a href="#" class="btn btn-outline-primary mt-auto o_editable">Get Started Free</a>
        </div>
      </div>
      <div class="col-md-5 col-lg-4">
        <div class="card border-0 shadow-lg p-4 text-center h-100 position-relative" style="border: 2px solid var(--color-primary, #007bff) !important;">
          <span class="badge bg-primary position-absolute top-0 start-50 translate-middle px-3 py-2 o_editable">Most Popular</span>
          <h4 class="fw-semibold mt-2 o_editable">Professional</h4>
          <div class="display-5 fw-bold my-3 o_editable">$99<span class="fs-6 fw-normal text-muted">/mo</span></div>
          <p class="text-muted small o_editable">For growing teams that need more power.</p>
          <ul class="list-unstyled text-start text-muted mt-3 mb-4">
            <li class="mb-2 o_editable"><span class="text-success me-2">&#10003;</span>Unlimited users</li>
            <li class="mb-2 o_editable"><span class="text-success me-2">&#10003;</span>All features</li>
            <li class="mb-2 o_editable"><span class="text-success me-2">&#10003;</span>Priority support</li>
            <li class="o_editable"><span class="text-success me-2">&#10003;</span>Advanced analytics</li>
          </ul>
          <a href="#" class="btn btn-primary mt-auto o_editable">Start 14-Day Trial</a>
        </div>
      </div>
    </div>
  </div>
</section>
```

---

### TEAM — Three-Column Person Cards

```html
<section class="o_colored_level py-5 bg-light">
  <div class="container">
    <div class="text-center mb-5">
      <h2 class="fw-bold o_editable">Meet the Team</h2>
      <p class="text-muted o_editable">The people behind our work.</p>
    </div>
    <div class="row g-4 justify-content-center">
      <div class="col-sm-6 col-lg-4">
        <div class="card border-0 shadow-sm text-center p-4">
          <img
            src="https://placehold.co/120x120/CCC/555?text=Photo"
            class="rounded-circle mx-auto mb-3"
            style="width:100px;height:100px;object-fit:cover;"
            alt="Team member"
          />
          <h5 class="fw-semibold o_editable">Jane Smith</h5>
          <p class="text-primary small fw-semibold mb-2 o_editable">Chief Executive Officer</p>
          <p class="text-muted small o_editable">Brief bio in one or two sentences. What's their expertise?</p>
        </div>
      </div>
      <div class="col-sm-6 col-lg-4">
        <div class="card border-0 shadow-sm text-center p-4">
          <img
            src="https://placehold.co/120x120/CCC/555?text=Photo"
            class="rounded-circle mx-auto mb-3"
            style="width:100px;height:100px;object-fit:cover;"
            alt="Team member"
          />
          <h5 class="fw-semibold o_editable">Mark Johnson</h5>
          <p class="text-primary small fw-semibold mb-2 o_editable">Head of Product</p>
          <p class="text-muted small o_editable">Brief bio in one or two sentences. What's their expertise?</p>
        </div>
      </div>
      <div class="col-sm-6 col-lg-4">
        <div class="card border-0 shadow-sm text-center p-4">
          <img
            src="https://placehold.co/120x120/CCC/555?text=Photo"
            class="rounded-circle mx-auto mb-3"
            style="width:100px;height:100px;object-fit:cover;"
            alt="Team member"
          />
          <h5 class="fw-semibold o_editable">Sarah Lee</h5>
          <p class="text-primary small fw-semibold mb-2 o_editable">Lead Designer</p>
          <p class="text-muted small o_editable">Brief bio in one or two sentences. What's their expertise?</p>
        </div>
      </div>
    </div>
  </div>
</section>
```

---

### STATS / NUMBERS BAR

```html
<section class="o_colored_level py-5 bg-primary text-white text-center">
  <div class="container">
    <div class="row g-4">
      <div class="col-6 col-md-3">
        <div class="display-4 fw-bold o_editable">500+</div>
        <p class="mb-0 text-white-50 o_editable">Happy Clients</p>
      </div>
      <div class="col-6 col-md-3">
        <div class="display-4 fw-bold o_editable">98%</div>
        <p class="mb-0 text-white-50 o_editable">Satisfaction Rate</p>
      </div>
      <div class="col-6 col-md-3">
        <div class="display-4 fw-bold o_editable">12</div>
        <p class="mb-0 text-white-50 o_editable">Countries</p>
      </div>
      <div class="col-6 col-md-3">
        <div class="display-4 fw-bold o_editable">10y</div>
        <p class="mb-0 text-white-50 o_editable">In Business</p>
      </div>
    </div>
  </div>
</section>
```

---

### CONTACT / LEAD FORM

```html
<section class="s_website_form o_colored_level py-5">
  <div class="container">
    <div class="row justify-content-center">
      <div class="col-lg-7 text-center mb-5">
        <h2 class="fw-bold o_editable">Get in Touch</h2>
        <p class="text-muted o_editable">Fill out the form and we'll get back to you within 24 hours.</p>
      </div>
    </div>
    <div class="row justify-content-center">
      <div class="col-lg-6">
        <div class="mb-3">
          <label class="form-label fw-semibold o_editable">Your Name</label>
          <input type="text" class="form-control" placeholder="Jane Smith" />
        </div>
        <div class="mb-3">
          <label class="form-label fw-semibold o_editable">Email Address</label>
          <input type="email" class="form-control" placeholder="jane@example.com" />
        </div>
        <div class="mb-3">
          <label class="form-label fw-semibold o_editable">Company (optional)</label>
          <input type="text" class="form-control" placeholder="Acme Corp" />
        </div>
        <div class="mb-4">
          <label class="form-label fw-semibold o_editable">Message</label>
          <textarea class="form-control" rows="5" placeholder="How can we help?"></textarea>
        </div>
        <a href="#" class="btn btn-primary w-100 btn-lg o_editable">Send Message</a>
        <p class="text-muted text-center small mt-3 o_editable">
          We respect your privacy. No spam, ever.
        </p>
      </div>
    </div>
  </div>
</section>
```

> Note: In Odoo's editor, you can replace this placeholder form with the native form builder widget for actual lead capture.

---

### LOGO BAR / CLIENTS

```html
<section class="o_colored_level py-4 bg-light">
  <div class="container">
    <p class="text-center text-muted small fw-semibold text-uppercase mb-4 o_editable" style="letter-spacing:.1em;">
      Trusted by teams at
    </p>
    <div class="row align-items-center justify-content-center g-4 text-center">
      <div class="col-6 col-md-2">
        <img src="https://placehold.co/120x40/EEE/999?text=Client+1" class="img-fluid" alt="Client 1" style="filter:grayscale(1);opacity:.6;">
      </div>
      <div class="col-6 col-md-2">
        <img src="https://placehold.co/120x40/EEE/999?text=Client+2" class="img-fluid" alt="Client 2" style="filter:grayscale(1);opacity:.6;">
      </div>
      <div class="col-6 col-md-2">
        <img src="https://placehold.co/120x40/EEE/999?text=Client+3" class="img-fluid" alt="Client 3" style="filter:grayscale(1);opacity:.6;">
      </div>
      <div class="col-6 col-md-2">
        <img src="https://placehold.co/120x40/EEE/999?text=Client+4" class="img-fluid" alt="Client 4" style="filter:grayscale(1);opacity:.6;">
      </div>
      <div class="col-6 col-md-2">
        <img src="https://placehold.co/120x40/EEE/999?text=Client+5" class="img-fluid" alt="Client 5" style="filter:grayscale(1);opacity:.6;">
      </div>
    </div>
  </div>
</section>
```

---

## Design Do's and Don'ts

### Do's
- Wrap all content in `.container` (not `.container-fluid` unless full-bleed is intentional)
- Use `py-5` as the default vertical rhythm on every `<section>`
- Add `o_editable` to every text block and button
- Add `o_colored_level` to every `<section>` (enables background color picker)
- Use `img-fluid` on every image
- Use semantic HTML: `<section>`, `<h1>`–`<h6>`, `<p>`, `<ul>`, `<nav>`
- Keep inline styles to a minimum — use utility classes
- Use `<a>` tags for buttons (not `<button>`)
- Use `g-4` or `g-5` gap on `.row` for card grid layouts

### Don'ts
- Don't use `<html>`, `<head>`, or `<body>` tags in the arch
- Don't use `id=""` attributes on snippet elements (multiple instances will conflict)
- Don't add `<script>` tags to page arch — use `scaffold_snippet.py` for JS
- Don't use element IDs for targeting — use classes only
- Don't nest `.container` inside `.container`
- Don't use BS5-only classes (`gap-*`, `d-grid`, `fs-*`) on Odoo 15/14 installs
- Don't use hardcoded px values for layout — use Bootstrap spacing scale
- Don't use `!important` unless absolutely necessary (breaks editor inline styles)
- Don't use third-party CSS frameworks alongside Bootstrap — conflicts will occur
- Don't put `<style>` blocks at the bottom of a section — put them at the top of the draft file or use a snippet module for scoped CSS
