from __future__ import annotations
from app.imagegen.gateway import build_prompt, ImageGateway
from app.persistence.image_store import ImageStore


class VisualAnchorService:
    """视觉锚定：风格参考图 + 角色定义图。"""

    def __init__(self, image_gateway: ImageGateway, image_store: ImageStore):
        self.imagegen = image_gateway
        self.store = image_store

    async def generate_style_reference(self, world_id: str, visual_style: dict, seed: int = 42) -> str:
        prompt = build_prompt(visual_style, "一个代表此世界整体视觉风格的概念图")
        data = await self.imagegen.generate(prompt=prompt, seed=seed)
        path = self.store.save(world_id=world_id, image_id="style-ref", data=data, ext="png")
        return path

    async def generate_character_ref(self, world_id: str, char_id: str, description: str, visual_style: dict, seed: int = 0) -> str:
        prompt = build_prompt(visual_style, f"角色立绘：{description}")
        data = await self.imagegen.generate(prompt=prompt, seed=seed)
        path = self.store.save(world_id=world_id, image_id=f"char-{char_id}", data=data, ext="png")
        return path
