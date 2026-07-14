"""种子脚本：创建艾尔德兰世界（YAML 文件），用于真实 LLM 模拟。

运行：cd backend && .venv/Scripts/python.exe scripts/seed_world.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from app.config import get_settings
from app.persistence.world_store import WorldStore

WORLD_NAME = "艾尔德兰"


def seed():
    settings = get_settings()
    worlds_dir = Path(settings.worlds_dir)
    worlds_dir.mkdir(parents=True, exist_ok=True)
    world_dir = worlds_dir / WORLD_NAME

    store = WorldStore()

    # 幂等：已存在则跳过
    if store.world_exists(world_dir):
        print(f"{WORLD_NAME} 已存在，跳过种子。")
        return

    world_dict = {
        "id": WORLD_NAME,
        "name": WORLD_NAME,
        "vision": "魔法衰落的王国",
        "setting": (
            "三年前寂灭之乱后魔法急剧衰退，旧贵族死守权力，流亡者在边境集结。"
            "冬月风雪，流亡骑士归来。"
        ),
        "rules": ["魔法稀有，施法付代价", "暴力会被通缉", "誓言有约束力", "冬夜不收外乡人"],
        "visual_style": {"art_style": "电影感写实", "palette": "冷峻墨蓝"},
        "clock_tick": 0,
        "clock_date": "冬月十四",
        "state_flags": {"war": False},
        "initial_state": {"opening": "流亡骑士艾伦雪夜归来", "inciting": "酒馆对峙"},
        "characters": [
            {
                "id": "艾伦",
                "name": "艾伦",
                "archetype": "流亡骑士",
                "personality": {
                    "neuroticism": 0.8,
                    "conscientiousness": 0.7,
                    "openness": 0.4,
                },
                "backstory": "曾是王国骑士，三年前被凯尔设局陷害而流亡北境。今夜归来寻仇。",
                "skills": ["剑术", "生存", "骑术"],
                "goals": {"short_term": "质问贝拉", "long_term": "揭露凯尔的阴谋"},
                "state": {"location_id": "断刃酒馆", "health": 100, "mood": "愤怒"},
            },
            {
                "id": "贝拉",
                "name": "贝拉",
                "archetype": "酒馆老板娘",
                "personality": {"agreeableness": 0.6, "neuroticism": 0.7},
                "backstory": "艾伦旧爱，三年前被凯尔威胁而背叛艾伦。经营寒鸦镇「断刃」酒馆。",
                "skills": ["人脉", "机敏", "隐忍"],
                "goals": {"short_term": "守住秘密", "long_term": "保护孩子"},
                "state": {"location_id": "断刃酒馆", "health": 90, "mood": "恐惧"},
            },
            {
                "id": "凯尔",
                "name": "凯尔",
                "archetype": "宫廷谋士",
                "personality": {"machiavellianism": 0.9, "emotional_stability": 0.8},
                "backstory": "王国实际操盘者，三年前设局清除异己。在王城谋士塔运筹帷幄。",
                "skills": ["权术", "冷酷", "耐心"],
                "goals": {"short_term": "观望", "long_term": "让王国在内乱中重建秩序"},
                "state": {"location_id": "谋士塔", "health": 100, "mood": "平静"},
            },
        ],
        "locations": [
            {"id": "断刃酒馆", "name": "断刃酒馆", "occupants": ["艾伦", "贝拉"]},
            {"id": "寒鸦镇集市", "name": "寒鸦镇集市"},
            {"id": "谋士塔", "name": "王城谋士塔", "occupants": ["凯尔"]},
            {"id": "北境营地", "name": "北境营地"},
            {"id": "雪松林神殿", "name": "雪松林神殿"},
        ],
        "relationships": [
            {"from": "艾伦", "to": "贝拉", "affinity": -35, "trust": -20},
            {"from": "艾伦", "to": "凯尔", "affinity": -80, "trust": -90},
            {"from": "贝拉", "to": "凯尔", "affinity": -10, "trust": -30},
        ],
    }

    store.save_world(world_dir, world_dict)

    print(f"世界创建: {WORLD_NAME}")
    print(f"  {world_dir / 'world.yaml'}")
    print(f"角色: 艾伦、贝拉、凯尔")
    print(f"地点: 5 个")
    print(f"\n种子完成！")
    print(f"启动模拟: POST /worlds/{WORLD_NAME}/simulate/start")
    print(f"推进:     POST /worlds/{WORLD_NAME}/simulate/step")


if __name__ == "__main__":
    seed()
