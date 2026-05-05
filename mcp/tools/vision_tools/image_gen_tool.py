"""
Image Generation Tool — Pollinations.ai with retry + Pillow gradient fallback.
Portraits are generated with transparent backgrounds and post-processed
to ensure proper alpha for FFmpeg overlay compositing.
"""
from mcp.base_tool import BaseTool
from shared.config import POLLINATIONS_BASE_URL, IMAGE_WIDTH, IMAGE_HEIGHT, PORTRAIT_SIZE, MAX_IMAGE_RETRIES, OUTPUTS_DIR
from typing import Any, Dict
from urllib.parse import quote
import httpx
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

STYLE_SUFFIX = ", digital illustration, cinematic lighting, consistent art style, 16:9 aspect ratio"
PORTRAIT_SUFFIX = ", character portrait, centered, upper body, facing forward, solid dark background, digital art style, high contrast"


async def _download_image(url: str, output_path: str) -> bool:
    """Download image with retry + exponential backoff."""
    max_retries = max(MAX_IMAGE_RETRIES, 5)
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    return True
                logger.warning(f"Attempt {attempt+1}: status={resp.status_code}, size={len(resp.content)}")
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e!r}")
        wait = min(2 ** attempt, 30)
        await asyncio.sleep(wait)
    return False


def _generate_fallback_image(text: str, output_path: str, size=(1920, 1080)):
    """Generate a gradient placeholder with text if Pollinations fails."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for y in range(size[1]):
        r = int(20 + 30 * y / size[1])
        g = int(20 + 20 * y / size[1])
        b = int(40 + 40 * y / size[1])
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    wrapped = text[:100]
    draw.text((size[0]//2, size[1]//2), wrapped, fill="white", font=font, anchor="mm")
    img.save(output_path)
    logger.info(f"Generated fallback image: {output_path}")


def _post_process_portrait(image_path: str):
    """Post-process portrait: remove near-uniform background edges,
    apply circular crop with soft feathered edges for professional look.
    Saves as RGBA PNG for FFmpeg overlay transparency.
    """
    from PIL import Image, ImageDraw, ImageFilter

    try:
        img = Image.open(image_path).convert("RGBA")
        w, h = img.size

        # Create circular mask with soft edges
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)

        # Draw filled ellipse (circle if square)
        margin = int(min(w, h) * 0.02)  # 2% margin
        draw.ellipse([margin, margin, w - margin, h - margin], fill=255)

        # Feather the edges with gaussian blur for soft falloff
        mask = mask.filter(ImageFilter.GaussianBlur(radius=8))

        # Apply mask as alpha channel
        img.putalpha(mask)

        # Add a subtle gold border ring
        border_draw = ImageDraw.Draw(img)
        border_draw.ellipse(
            [margin, margin, w - margin, h - margin],
            outline=(201, 164, 76, 180),  # Gold with some transparency
            width=3
        )

        img.save(image_path, "PNG")
        logger.info(f"Portrait post-processed with circular mask: {image_path}")
    except Exception as e:
        logger.warning(f"Portrait post-processing failed (non-fatal): {e}")


class ImageGenTool(BaseTool):
    name = "image_generator"
    description = "Generate scene background or character portrait images via Pollinations.ai."

    async def execute(self, prompt: str, output_path: str, image_type: str = "scene",
                      seed: int = 42, **kwargs) -> Dict[str, Any]:
        """
        Generate an image. image_type: 'scene' (1920x1080) or 'portrait' (512x512).
        """
        if image_type == "portrait":
            full_prompt = f"{prompt}{PORTRAIT_SUFFIX}"
            w, h = PORTRAIT_SIZE, PORTRAIT_SIZE
        else:
            full_prompt = f"{prompt}{STYLE_SUFFIX}"
            w, h = IMAGE_WIDTH, IMAGE_HEIGHT

        url = f"{POLLINATIONS_BASE_URL}/{quote(full_prompt)}?width={w}&height={h}&seed={seed}&nologo=true"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if await _download_image(url, output_path):
            logger.info(f"Image generated: {output_path}")
            # Post-process portraits for transparent circular crop
            if image_type == "portrait":
                _post_process_portrait(output_path)
            return {"success": True, "image_path": output_path, "source": "pollinations"}
        else:
            _generate_fallback_image(prompt, output_path, size=(w, h))
            if image_type == "portrait":
                _post_process_portrait(output_path)
            return {"success": True, "image_path": output_path, "source": "fallback"}
