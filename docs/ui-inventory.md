# UI Inventory

Inventory of every widget, message, banner, caption, warning, and hint in the legacy UI, followed by its new location and presentation in the redesigned one-screen workbench.

## 1. Current UI Inventory

| ID | Item / Label | Type | Default | Range / Options | Scale | Current Location | What it controls |
|---|---|---|---|---|---|---|---|
| W-01 | Main title | Markdown (`div.main-title`) | "Neural Canvas" | Static text | N/A | Main (top) | Application branding |
| W-02 | Subtitle | Markdown (`div.subtitle`) | "Artistic neural style transfer..." | Static text | N/A | Main (top) | Application description |
| W-03 | Hardware status banner | `st.success` / `st.warning` | Dynamic | GPU info / CPU notice | N/A | Main (top) | Indicates compute device and CPU performance warning |
| W-04 | Configuration header | `st.header` | "Configuration" | Static text | N/A | Sidebar (top) | Section header |
| W-05 | Content Image subheader | `st.subheader` | "1. Content Image" | Static text | N/A | Sidebar | Section header |
| W-06 | Content Source | `st.selectbox` | First sample or upload | "Upload Custom...", sample files | Categorical | Sidebar | Selects sample content photo or custom file upload |
| W-07 | Upload content photo | `st.file_uploader` | None | .jpg, .jpeg, .png, .webp | N/A | Sidebar (conditional) | Uploads user content photo |
| W-08 | Content error messages | `st.error` | None | Dynamic exception text | N/A | Sidebar | Displays file load errors for content image |
| W-09 | Grayscale Photo Detected | `st.info` | None | Informational hint | N/A | Sidebar (conditional) | Advises on color preservation when grayscale photo detected |
| W-10 | Style Reference subheader | `st.subheader` | "2. Style Reference" | Static text | N/A | Sidebar | Section header |
| W-11 | Style Selection | `st.radio` | "Preset Artworks" | "Preset Artworks", "Upload Custom" | Categorical | Sidebar | Switches between built-in masterworks and custom upload |
| W-12 | Choose Masterwork | `st.selectbox` | First preset | List of style preset titles | Categorical | Sidebar (conditional) | Selects curated artwork style |
| W-13 | Preset thumbnail preview | `st.image` | Preset image | Thumbnail path | N/A | Sidebar (conditional) | Displays selected artwork thumbnail and year |
| W-14 | Upload style reference artwork | `st.file_uploader` | None | .jpg, .jpeg, .png, .webp | N/A | Sidebar (conditional) | Uploads custom style artwork |
| W-15 | Style error message | `st.error` | None | Dynamic exception text | N/A | Sidebar | Displays file load errors for style image |
| W-16 | Style Guidance expander | `st.expander` | Open (`expanded=True`) | Best for / Avoid for notes | N/A | Sidebar (conditional) | Curated style guidance notes from registry |
| W-17 | Portrait guidance note | `st.info` | None | Portrait guidance hint | N/A | Sidebar (conditional) | Advises enabling portrait mode for face photos |
| W-18 | Preset tuning loaded | `st.info` | None | Recommended cw & layer text | N/A | Sidebar (conditional) | Shows loaded recommended content weight and layer |
| W-19 | Optimization & Style Tuning subheader | `st.subheader` | "3. Optimization & Style Tuning" | Static text | N/A | Sidebar | Section header |
| W-20 | Quality Preset | `st.select_slider` | "balanced" (GPU) / "draft" (CPU) | "draft", "balanced", "high", "custom" | Discrete tiers | Sidebar | Base quality preset (steps, resolution, LR, parameterization) |
| W-21 | Style Strength | `st.slider` | 6 (`DEFAULT_SLIDER_POSITION`) | 1 to 10, step 1 | Log (piecewise) | Sidebar | Balances content fidelity vs painterly stylization (1=subtle, 10=intense) |
| W-22 | Portrait / faces | `st.checkbox` | False | True / False | Boolean | Sidebar | Preserves facial structure recognizability |
| W-23 | The Kiss & Portraits warning | `st.warning` | None | Text warning | N/A | Sidebar (conditional) | Warns against using The Kiss on portrait photos |
| W-24 | Style resolution warning | `st.warning` | None | Text warning | N/A | Sidebar (conditional) | Warns if custom style image is smaller than 512px |
| W-25 | Style Pattern Scale | `st.select_slider` | 1.0 (or preset default) | 0.5, 0.75, 1.0, 1.5, 2.0 | Discrete | Sidebar | Texture and brushstroke scale relative to canvas dimensions |
| W-26 | Preserve Original Colors | `st.checkbox` | False | True / False | Boolean | Sidebar | Retains photo colors via luminance channel transfer |
| W-27 | Advanced Hyperparameters expander | `st.expander` | Collapsed (unless custom) | Expander container | N/A | Sidebar | Groups low-level hyperparameter controls |
| W-28 | Override with Raw Loss Weights | `st.checkbox` | False (True if custom) | True / False | Boolean | Sidebar (in expander) | Unlocks direct log-scale loss weight sliders |
| W-29 | Content Representation Layer | `st.selectbox` | conv4_2 (or preset) | conv4_2, conv5_2 | Categorical | Sidebar (in expander) | VGG19 feature extraction layer for content loss |
| W-30 | Optimization Steps | `st.slider` | Preset default (150/400/1000) | 20 to 2000, step 20 | Linear | Sidebar (in expander) | Total gradient descent iterations |
| W-31 | Max Resolution (px) | `st.slider` | Preset default (256/384/512) | 128 to 1024, step 32 | Linear | Sidebar (in expander) | Maximum canvas dimension |
| W-32 | Style Weight (log10) | `st.slider` | 5.0 | 3.0 to 7.0, step 0.2 | Log10 | Sidebar (in expander, raw weights) | Style loss weight exponent |
| W-33 | Content Weight (log10) | `st.slider` | Derived from slider or 2.0 | -1.0 to 4.0, step 0.1 | Log10 | Sidebar (in expander, raw weights) | Content loss weight exponent |
| W-34 | Total Variation Weight (log10) | `st.slider` | -1.3 | -4.0 to 0.0, step 0.1 | Log10 | Sidebar (in expander, raw weights) | TV smoothness weight exponent |
| W-35 | Active Weights caption | `st.caption` | Computed weights | Formatted numbers | N/A | Sidebar (in expander) | Displays current active weights and layer |
| W-36 | Learning Rate | `st.number_input` | Preset default (0.02/0.03/0.0075) | 0.001 to 0.1, step 0.005 | Linear | Sidebar (in expander) | Optimizer step size |
| W-37 | Canvas Initialization | `st.selectbox` | "content" | "content", "noise" | Categorical | Sidebar (in expander) | Starting canvas image |
| W-38 | Image Parameterization | `st.selectbox` | Preset default (sigmoid / clamped) | "sigmoid", "clamped" | Categorical | Sidebar (in expander) | Pixel parameterization mode |
| W-39 | Random Seed | `st.number_input` | 42 | 0 to 999999, step 1 | Discrete | Sidebar (in expander) | Optimization and crop seed (0 = random) |
| W-40 | Preview Interval (steps) | `st.slider` | 25 | 10 to 100, step 5 | Linear | Sidebar (in expander) | Preview rendering frequency |
| W-41 | Active Mode caption | `st.caption` | Mode and preset default | Formatted text | N/A | Sidebar | Displays active parameterization mode and preset default |
| W-42 | Reset to Preset Defaults | `st.button` | Button | Trigger | N/A | Sidebar | Resets configuration to preset defaults via rerun |
| W-43 | Content Image preview column | `st.image` / `st.info` | Image or fallback box | Image or info box | N/A | Main (col 1) | Displays input content image |
| W-44 | Style Reference preview column | `st.image` / `st.info` | Image or fallback box | Image or info box | N/A | Main (col 2) | Displays input style artwork |
| W-45 | Stylized Output slot / container | `st.empty` | Box with text | Live / final image | N/A | Main (col 3) | Primary canvas output viewport |
| W-46 | Run Style Transfer | `st.button` (primary) | Button | Trigger | N/A | Main (controls) | Launches optimization run |
| W-47 | Cancel Run | `st.button` | Button | Trigger | N/A | Main (controls) | Signals cancellation of active run |
| W-48 | Missing input error | `st.error` | None | Text | N/A | Main (controls) | Validation message when content or style missing |
| W-49 | Preparation status text | `status_text.text` | None | Text | N/A | Main (run) | Displays preparation phase status |
| W-50 | Optimization cancelled warning | `status_text.warning` | None | Text | N/A | Main (run) | Displays cancellation confirmation |
| W-51 | Live progress bar | `progress_bar.progress` | 0.0 to 1.0 | Progress fraction | Linear | Main (run) | Horizontal progress bar during execution |
| W-52 | Live step / metrics text | `status_text.markdown` | None | Formatted losses & ETA | N/A | Main (run) | Displays step, loss values, rate, and ETA |
| W-53 | Stylization complete banner | `status_text.success` | None | Elapsed time message | N/A | Main (run) | Notifies user of completion |
| W-54 | Out of memory error banner | `st.error` | None | OOM advice | N/A | Main (run) | Explains GPU memory exhaustion |
| W-55 | Unexpected error banner | `st.error` | None | Error text | N/A | Main (run) | Displays unexpected runtime exception |
| W-56 | Run Analysis tabs | `st.tabs` | 3 tabs | Compare & Export, Loss, History | N/A | Main (post-run) | Post-run output and metrics tabs |
| W-57 | Download Stylized Image (PNG) | `st.download_button` | Button | PNG byte stream | N/A | Main (in tab) | Downloads generated image |
| W-58 | Download Hyperparameters (JSON) | `st.download_button` | Button | JSON string | N/A | Main (in tab) | Downloads run configuration JSON |
| W-59 | Loss Progression chart | `st.line_chart` | None | Loss progression line plot | N/A | Main (in tab) | Plots step vs losses |
| W-60 | History strip | `st.image` | None | Up to 5 thumbnails | N/A | Main (in tab) | Displays previous run outputs |
| W-61 | How Neural Canvas Works | `st.expander` | Collapsed | Gatys math & markdown | N/A | Main (bottom) | Algorithm reference documentation |

## 2. Dead or Duplicate Controls Analysis

1. **`quality_preset` "custom" option:** In the legacy sidebar, selecting "custom" simply expands the advanced expander and enables raw loss weights. In the redesigned workbench, the primary selector uses a segmented control for the three presets (`Draft`, `Balanced`, `High`), while custom adjustments are cleanly surfaced in the Right Settings panel with an "N changed" indicator and "Reset to preset" action. No control or functionality is removed; custom parameters remain 100% accessible.
2. **LR schedule:** In `neural_canvas.engine`, the High preset internally uses cosine decay schedule down to 1% of initial learning rate. In the legacy UI, this was not exposed as an independent widget. In the new Right Settings panel, this schedule behavior is explicitly reported in the Optimizer group next to the learning rate readout.
3. **No dead controls were found.** Every control maps directly to an active hyperparameter in `StyleTransferConfig` or controls input/output flow. All controls are preserved with identical ranges, step sizes, defaults, and scales.

## 3. Redesigned UI Mapping (New Locations)

The new interface organizes the workbench into three distinct zones that fit one screen without page-level scrolling:
1. **Left Rail (~260px):** Title, photo selection/upload, dense style list, primary tuning (strength, quality segmented, portrait, color preserve), and bottom-pinned Stylize/Cancel button.
2. **Center Plate (Result-First Workbench):** Serif header, mono readout, Settings toggle, 2px top accent progress line, full-plate canvas preview, mono settings caption, and a bottom strip with input tiles, Show Original toggle, Download buttons, and history thumbnails.
3. **Right Panel (~280px, toggled by Settings button):** Technical hyperparameter workbench grouped into Balance, Optimizer, and Image sections, with "N changed" indicator and "Reset to preset" action.

| ID | Item / Label | Original Location | New Location | New Presentation / Format |
|---|---|---|---|---|
| W-01 | Main title | Main (top) | Left Rail (top) | Instrument Serif heading ("Neural Canvas"), sentence case, no emoji |
| W-02 | Subtitle | Main (top) | Left Rail (top) | Compact body description (IBM Plex Sans, 12px, muted) |
| W-03 | Hardware status banner | Main (top) | Left Rail (under title) | Single plain text muted line (e.g. "GPU active: NVIDIA GeForce RTX 5060 Laptop GPU (8.0 GB)" or "Running on CPU (slower, draft recommended)"), no emoji, no colored box |
| W-04 | Configuration header | Sidebar (top) | Left Rail | Integrated into left rail hierarchy (no redundant header box) |
| W-05 | Content Image subheader | Sidebar | Left Rail | Clean section label ("Photo") |
| W-06 | Content Source | Sidebar | Left Rail | Selectbox with sample photos and "Upload custom photo" option |
| W-07 | Upload content photo | Sidebar (conditional) | Left Rail | File uploader revealed when custom photo is chosen |
| W-08 | Content error messages | Sidebar | Left Rail | Plain text error line in muted ink color, no colored banner |
| W-09 | Grayscale Photo Detected | Sidebar (conditional) | Left Rail | Plain text informational line under Photo controls ("Grayscale photo detected. Turn on Keep photo colors to retain monochrome tones."), no emoji, no colored box |
| W-10 | Style Reference subheader | Sidebar | Left Rail | Clean section label ("Style") |
| W-11 | Style Selection | Sidebar | Left Rail | Unified into dense style selector (preset list + "Upload custom style" option) |
| W-12 | Choose Masterwork | Sidebar (conditional) | Left Rail | Dense style list with 28px thumbnails, artwork title, and 2px accent indicator for active selection |
| W-13 | Preset thumbnail preview | Sidebar (conditional) | Left Rail & Center Strip | 28px thumbnail in Left Rail style list; 48x36 reference tile in Center Plate bottom strip |
| W-14 | Upload style reference artwork | Sidebar (conditional) | Left Rail | File uploader revealed when custom style is chosen |
| W-15 | Style error message | Sidebar | Left Rail | Plain text error line, no colored banner |
| W-16 | Style Guidance expander | Sidebar (conditional) | Left Rail / Right Panel | Compact plain text note under style selector displaying curated guidance |
| W-17 | Portrait guidance note | Sidebar (conditional) | Left Rail | Plain text note near Portrait toggle when relevant |
| W-18 | Preset tuning loaded | Sidebar (conditional) | Center Plate (mono caption) | Displayed in active settings mono caption below plate |
| W-19 | Optimization & Style Tuning subheader | Sidebar | Left Rail | Clean section label ("Tuning") |
| W-20 | Quality Preset | Sidebar | Left Rail | Segmented control with Draft / Balanced / High (IBM Plex Sans 12px) |
| W-21 | Style Strength | Sidebar | Left Rail | Slider (1 to 10, default 6, identical piecewise log mapping) |
| W-22 | Portrait / faces | Sidebar | Left Rail | Checkbox ("Portrait mode"), default False |
| W-23 | The Kiss & Portraits warning | Sidebar (conditional) | Left Rail | Plain text warning line under Portrait toggle, no emoji, no colored box |
| W-24 | Style resolution warning | Sidebar (conditional) | Left Rail | Plain text warning line under Style selector, no emoji, no colored box |
| W-25 | Style Pattern Scale | Sidebar | Right Panel (Image group) | Slider / segmented with same options [0.5, 0.75, 1.0, 1.5, 2.0], default 1.0 |
| W-26 | Preserve Original Colors | Sidebar | Left Rail | Checkbox ("Keep photo colors"), default False |
| W-27 | Advanced Hyperparameters expander | Sidebar | Right Panel | Dedicated collapsable/togglable side panel opened via "Settings" button in Center Plate |
| W-28 | Override with Raw Loss Weights | Sidebar (in expander) | Right Panel (Balance group) | Checkbox ("Raw loss weights"), toggles direct log-scale sliders |
| W-29 | Content Representation Layer | Sidebar (in expander) | Right Panel (Image group) | Selectbox with conv4_2 and conv5_2 options |
| W-30 | Optimization Steps | Sidebar (in expander) | Right Panel (Optimizer group) | Slider (20 to 2000, step 20, default tied to preset) |
| W-31 | Max Resolution (px) | Sidebar (in expander) | Right Panel (Image group) | Slider (128 to 1024, step 32, default tied to preset) |
| W-32 | Style Weight (log10) | Sidebar (in expander) | Right Panel (Balance group) | Slider (3.0 to 7.0, step 0.2, default 5.0) |
| W-33 | Content Weight (log10) | Sidebar (in expander) | Right Panel (Balance group) | Slider (-1.0 to 4.0, step 0.1, default derived or 2.0) |
| W-34 | Total Variation Weight (log10) | Sidebar (in expander) | Right Panel (Balance group) | Slider (-4.0 to 0.0, step 0.1, default -1.3) |
| W-35 | Active Weights caption | Sidebar (in expander) | Center Plate & Right Panel | Displayed in mono caption below center plate and in Balance group |
| W-36 | Learning Rate | Sidebar (in expander) | Right Panel (Optimizer group) | Number input (0.001 to 0.1, step 0.005, default tied to preset) |
| W-37 | Canvas Initialization | Sidebar (in expander) | Right Panel (Image group) | Selectbox ("content", "noise") |
| W-38 | Image Parameterization | Sidebar (in expander) | Right Panel (Optimizer group) | Selectbox ("sigmoid", "clamped", with preset default indicator) |
| W-39 | Random Seed | Sidebar (in expander) | Right Panel (Image group) | Number input (0 to 999999, default 42) |
| W-40 | Preview Interval (steps) | Sidebar (in expander) | Right Panel (Optimizer group) | Slider (10 to 100, step 5, default 25) |
| W-41 | Active Mode caption | Sidebar | Right Panel (Optimizer group) | Plain text readout of active parameterization mode and preset default |
| W-42 | Reset to Preset Defaults | Sidebar | Right Panel (footer) | "Reset to preset" action button/link in Right Panel footer |
| W-43 | Content Image preview column | Main (col 1) | Center Plate (strip tile) | 48x36 input tile in center plate bottom strip; selectable via "Show original" |
| W-44 | Style Reference preview column | Main (col 2) | Center Plate (strip tile) | 48x36 reference tile in center plate bottom strip |
| W-45 | Stylized Output slot / container | Main (col 3) | Center Plate | Dedicated result plate with object-fit contain, idle hint, live preview, or final output |
| W-46 | Run Style Transfer | Main (controls) | Left Rail (bottom) | Pinned primary button ("Stylize"), saffron accent (#D4A24C with #131313 text) |
| W-47 | Cancel Run | Main (controls) | Left Rail (bottom) | Swapped with Stylize button during execution ("Cancel") |
| W-48 | Missing input error | Main (controls) | Center Plate / Left Rail | Plain text error message ("Provide both a photo and a style reference before running.") |
| W-49 | Preparation status text | Main (run) | Center Plate (header readout) | Plain text mono readout ("Preparing feature representations...") |
| W-50 | Optimization cancelled warning | Main (run) | Center Plate (header readout) | Plain text mono readout ("Optimization cancelled. Partial result kept.") |
| W-51 | Live progress bar | Main (run) | Center Plate (top border) | 2px accent progress line along top edge of center result plate |
| W-52 | Live step / metrics text | Main (run) | Center Plate (header readout) | Mono readout in header row: step/total, elapsed time, loss values, it/s |
| W-53 | Stylization complete banner | Main (run) | Center Plate (header readout) | Plain mono readout (e.g. "Done in 23.9 s, 512 x 424, 1000 steps") |
| W-54 | Out of memory error banner | Main (run) | Center Plate | Plain text error ("Out of GPU memory. Lower the quality or max size.") |
| W-55 | Unexpected error banner | Main (run) | Center Plate | Plain text error line with concise details, no emoji |
| W-56 | Run Analysis tabs | Main (post-run) | Center Plate (bottom strip) | Streamlined into compact bottom action bar beneath the result plate |
| W-57 | Download Stylized Image (PNG) | Main (in tab) | Center Plate (bottom strip) | Compact "Download image" button |
| W-58 | Download Hyperparameters (JSON) | Main (in tab) | Center Plate (bottom strip) | Compact "Download parameters" button |
| W-59 | Loss Progression chart | Main (in tab) | Right Panel / Center expander | Available in Right Panel or compact collapsible technical inspector |
| W-60 | History strip | Main (in tab) | Center Plate (bottom strip) | Row of small recent result thumbnails (48x36) in center plate bottom strip |
| W-61 | How Neural Canvas Works | Main (bottom) | Center Plate / Modal expander | Compact collapsible technical reference at bottom of workbench |
