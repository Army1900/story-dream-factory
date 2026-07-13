import os


class ImageStore:
    """把图像字节存到本地文件系统，按 world_id 分目录。"""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def _ensure_dir(self, world_id: str) -> str:
        directory = os.path.join(self.base_dir, world_id)
        os.makedirs(directory, exist_ok=True)
        return directory

    def save(
        self, world_id: str, image_id: str, data: bytes, ext: str = "png"
    ) -> str:
        directory = self._ensure_dir(world_id)
        path = os.path.join(directory, f"{image_id}.{ext}")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def load(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def delete(self, path: str) -> None:
        if os.path.exists(path):
            os.remove(path)
