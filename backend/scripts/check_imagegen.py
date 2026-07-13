"""手动验证生图网关真实调用。需配置 ZHIPU_API_KEY。

运行：uv run python scripts/check_imagegen.py
"""
import asyncio
import os

from app.imagegen.gateway import ImageGateway


async def main():
    gw = ImageGateway(provider="zhipu")
    data = await gw.generate(prompt="油画风格，一座笼罩在暴风雨中的中世纪小镇", seed=42)
    out = os.path.join("data", "images", "check.png")
    os.makedirs("data/images", exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    print(f"saved {out} ({len(data)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
