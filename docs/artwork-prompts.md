# Artwork prompts

## Wallpaper

Use case: stylized-concept. Asset type: default Linux desktop wallpaper for RAVNUX. Create a high-resolution landscape 16:9 wallpaper, preferably 3840x2160. A realistic cinematic cyberpunk city at night with imposing towers, layered architecture and wet streets reflecting vivid PURPLE neon lights with pink accents, deep dark plum shadows, mist and subtle rain. Rich architectural detail, coherent perspective, atmospheric light, tasteful composition that remains comfortable as a desktop background. No people in foreground, no logos, no text, no watermarks, no desktop interface. Purple is the dominant neon color. Render only the wallpaper artwork.

## Logo

Use case: logo-brand. Asset type: Linux distribution RAVNUX logo icon. Exactly one uppercase letter "R", vivid pink on a deep purple background, decorated with gold edging, symmetrical gold ornaments, fine curved lines and diamond/star motifs. Keep the letter upright and clearly recognizable. No other letters, mockup, watermark or desktop interface. The recovered approved artwork is a 1254x1254 RGB PNG, stored directly at `overlay/common/usr/share/pixmaps/ravnux-logo.png`.

Integration: `scripts/build.sh` copies the common overlay into both the live filesystem and `/usr/share/ravnux/root-overlay`. `scripts/install.sh` copies that embedded overlay into the target system. LightDM uses the logo as its default user image; the offline guide uses it as its desktop-entry icon. No Base64 is stored in configuration or scripts.

Logo SHA256: `41ad8a1dd956756ac076d1e5af0430e4508f89f118408553a98d415b2be24bd0`.

Both assets use the built-in image generator. The generated PNG wallpaper is encoded as JPEG for desktop use, without resizing or changing its composition. Actual dimensions are recorded by the image files; requested sizes are generation preferences.
