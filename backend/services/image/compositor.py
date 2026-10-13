"""Image composition and typography overlay services using Pillow."""
import io
import os
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFont
import structlog

logger = structlog.get_logger(__name__)


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load a TrueType font with system fallback to PIL default font."""
    font_candidates = [
        # Windows font paths
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\calibrib.ttf" if bold else "C:\\Windows\\Fonts\\calibri.ttf",
        # Generic names for cross-platform / Linux fontconfig
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]

    for candidate in font_candidates:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue

    # Fallback to default font (size support depends on Pillow >= 10.1.0)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Break text into lines that fit within max_width pixels."""
    words = text.split()
    if not words:
        return []

    lines: List[str] = []
    current_line = words[0]

    for word in words[1:]:
        test_line = f"{current_line} {word}"
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines


class ImageCompositor:
    """High-quality visual ad compositor creating branded ad creatives."""

    @staticmethod
    def add_text_overlay(
        image_bytes: bytes,
        headline: str,
        subtext: str,
        cta_text: str,
        brand_name: str = "",
        colors: Optional[Dict[str, str]] = None,
    ) -> bytes:
        """Composite typography and brand overlays onto an ad image.
        
        Args:
            image_bytes: Input base image bytes.
            headline: Main attention-grabbing headline.
            subtext: Value proposition or secondary descriptive text.
            cta_text: Call-to-action button label.
            brand_name: Brand or business name.
            colors: Optional dict with keys: 'headline', 'subtext', 'cta_bg',
                    'cta_text', 'brand', 'card_bg'.

        Returns:
            PNG image bytes of composite image.
        """
        palette = {
            "headline": "#FFFFFF",
            "subtext": "#E2E8F0",
            "cta_bg": "#2563EB",
            "cta_text": "#FFFFFF",
            "brand": "#93C5FD",
            "card_bg": "#000000",
        }
        if colors:
            palette.update(colors)

        base_image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = base_image.size

        # Create transparent overlay for shapes and text
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Dynamic scale relative to standard 1024px reference
        scale = min(width, height) / 1024.0
        headline_size = max(24, int(46 * scale))
        subtext_size = max(16, int(26 * scale))
        cta_size = max(14, int(22 * scale))
        brand_size = max(12, int(20 * scale))

        headline_font = _get_font(headline_size, bold=True)
        subtext_font = _get_font(subtext_size, bold=False)
        cta_font = _get_font(cta_size, bold=True)
        brand_font = _get_font(brand_size, bold=True)

        padding_x = int(48 * scale)
        max_text_width = width - (padding_x * 2)

        # 1. Brand name at top
        current_y = int(40 * scale)
        if brand_name:
            brand_lines = _wrap_text(brand_name.upper(), brand_font, max_text_width, draw)
            for line in brand_lines:
                bbox = draw.textbbox((0, 0), line, font=brand_font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                # Subtle pill backdrop behind brand
                pill_pad_x = int(14 * scale)
                pill_pad_y = int(6 * scale)
                draw.rounded_rectangle(
                    [
                        padding_x - pill_pad_x,
                        current_y - pill_pad_y,
                        padding_x + tw + pill_pad_x,
                        current_y + th + pill_pad_y,
                    ],
                    radius=int(6 * scale),
                    fill=(0, 0, 0, 140),
                )
                draw.text(
                    (padding_x, current_y),
                    line,
                    font=brand_font,
                    fill=palette["brand"],
                )
                current_y += th + int(12 * scale)
            current_y += int(14 * scale)

        # 2. Headline with translucent backing card
        if headline:
            headline_lines = _wrap_text(headline, headline_font, max_text_width, draw)
            if headline_lines:
                card_top = current_y
                line_heights = []
                for line in headline_lines:
                    bbox = draw.textbbox((0, 0), line, font=headline_font)
                    line_heights.append(bbox[3] - bbox[1])
                total_hl_height = sum(line_heights) + (len(headline_lines) * int(10 * scale))

                # Draw backdrop card for high readability
                card_pad = int(16 * scale)
                draw.rounded_rectangle(
                    [
                        padding_x - card_pad,
                        card_top - card_pad,
                        width - padding_x + card_pad,
                        card_top + total_hl_height + card_pad,
                    ],
                    radius=int(12 * scale),
                    fill=(0, 0, 0, 160),
                )

                text_cursor_y = card_top
                for idx, line in enumerate(headline_lines):
                    draw.text(
                        (padding_x, text_cursor_y),
                        line,
                        font=headline_font,
                        fill=palette["headline"],
                    )
                    text_cursor_y += line_heights[idx] + int(10 * scale)

                current_y = text_cursor_y + int(16 * scale)

        # 3. Subtext in middle section
        if subtext:
            subtext_lines = _wrap_text(subtext, subtext_font, max_text_width, draw)
            if subtext_lines:
                sub_heights = []
                for line in subtext_lines:
                    bbox = draw.textbbox((0, 0), line, font=subtext_font)
                    sub_heights.append(bbox[3] - bbox[1])
                total_sub_height = sum(sub_heights) + (len(subtext_lines) * int(8 * scale))

                card_pad = int(12 * scale)
                draw.rounded_rectangle(
                    [
                        padding_x - card_pad,
                        current_y - card_pad,
                        width - padding_x + card_pad,
                        current_y + total_sub_height + card_pad,
                    ],
                    radius=int(8 * scale),
                    fill=(0, 0, 0, 130),
                )

                text_cursor_y = current_y
                for idx, line in enumerate(subtext_lines):
                    draw.text(
                        (padding_x, text_cursor_y),
                        line,
                        font=subtext_font,
                        fill=palette["subtext"],
                    )
                    text_cursor_y += sub_heights[idx] + int(8 * scale)

        # 4. CTA Button at bottom
        if cta_text:
            cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
            btn_text_w = cta_bbox[2] - cta_bbox[0]
            btn_text_h = cta_bbox[3] - cta_bbox[1]

            btn_pad_x = int(32 * scale)
            btn_pad_y = int(16 * scale)
            btn_w = btn_text_w + (btn_pad_x * 2)
            btn_h = btn_text_h + (btn_pad_y * 2)

            btn_x0 = padding_x
            btn_y0 = height - int(60 * scale) - btn_h
            btn_x1 = btn_x0 + btn_w
            btn_y1 = btn_y0 + btn_h

            # Parse CTA color
            try:
                cta_bg_rgb = ImageColor.getrgb(palette["cta_bg"])
                cta_bg_rgba = (*cta_bg_rgb, 240)
            except Exception:
                cta_bg_rgba = (37, 99, 235, 240)

            # Draw rounded CTA button
            draw.rounded_rectangle(
                [btn_x0, btn_y0, btn_x1, btn_y1],
                radius=int(10 * scale),
                fill=cta_bg_rgba,
            )

            # Center text inside CTA button
            btn_text_x = btn_x0 + (btn_w - btn_text_w) // 2
            btn_text_y = btn_y0 + (btn_h - btn_text_h) // 2
            draw.text(
                (btn_text_x, btn_text_y),
                cta_text,
                font=cta_font,
                fill=palette["cta_text"],
            )

        # Composite overlay with base image
        composed = Image.alpha_composite(base_image, overlay)
        buffer = io.BytesIO()
        composed.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def add_logo(
        image_bytes: bytes,
        logo_bytes: bytes,
        position: str = "bottom-right",
        size: int = 100,
    ) -> bytes:
        """Overlay a brand logo onto an ad creative.
        
        Args:
            image_bytes: Base creative image bytes.
            logo_bytes: Logo image bytes (transparent PNG recommended).
            position: 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'.
            size: Maximum bounding box dimension (width or height) in pixels.

        Returns:
            PNG image bytes with composite logo.
        """
        base_image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        logo_image = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        base_w, base_h = base_image.size

        # Maintain aspect ratio while fitting into size x size box
        logo_image.thumbnail((size, size), Image.Resampling.LANCZOS)
        logo_w, logo_h = logo_image.size

        margin = int(24 * (min(base_w, base_h) / 1024.0))
        margin = max(margin, 16)

        pos = position.strip().lower()
        if pos == "top-left":
            x, y = margin, margin
        elif pos == "top-right":
            x, y = base_w - logo_w - margin, margin
        elif pos == "bottom-left":
            x, y = margin, base_h - logo_h - margin
        elif pos == "center":
            x, y = (base_w - logo_w) // 2, (base_h - logo_h) // 2
        else:  # default 'bottom-right'
            x, y = base_w - logo_w - margin, base_h - logo_h - margin

        # Composite with alpha transparency
        overlay = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))
        overlay.paste(logo_image, (x, y), mask=logo_image)

        composed = Image.alpha_composite(base_image, overlay)
        buffer = io.BytesIO()
        composed.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def create_gradient_overlay(
        image_bytes: bytes,
        color1: str = "#000000",
        color2: str = "#000000",
        opacity: float = 0.5,
    ) -> bytes:
        """Create a smooth vertical linear gradient overlay.
        
        Args:
            image_bytes: Base image bytes.
            color1: Top hex color code.
            color2: Bottom hex color code.
            opacity: Maximum gradient opacity (0.0 to 1.0).

        Returns:
            PNG bytes with applied gradient.
        """
        base_image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = base_image.size

        try:
            rgb1 = ImageColor.getrgb(color1)
        except Exception:
            rgb1 = (0, 0, 0)

        try:
            rgb2 = ImageColor.getrgb(color2)
        except Exception:
            rgb2 = (0, 0, 0)

        gradient = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(gradient)

        # Draw line by line interpolation
        max_alpha = int(255 * max(0.0, min(1.0, opacity)))
        for y in range(height):
            ratio = y / max(1, height - 1)
            r = int(rgb1[0] * (1.0 - ratio) + rgb2[0] * ratio)
            g = int(rgb1[1] * (1.0 - ratio) + rgb2[1] * ratio)
            b = int(rgb1[2] * (1.0 - ratio) + rgb2[2] * ratio)
            # Quadratic ramp for natural photographic vignette / text legibility
            alpha = int(max_alpha * (ratio ** 1.3))
            draw.line([(0, y), (width, y)], fill=(r, g, b, alpha))

        composed = Image.alpha_composite(base_image, gradient)
        buffer = io.BytesIO()
        composed.save(buffer, format="PNG")
        return buffer.getvalue()


# Module-level aliases
add_text_overlay = ImageCompositor.add_text_overlay
add_logo = ImageCompositor.add_logo
create_gradient_overlay = ImageCompositor.create_gradient_overlay

