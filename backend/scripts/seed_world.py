"""种子脚本：创建艾尔德兰世界 + 3 角色，用于真实 LLM 模拟。

运行：cd backend && .venv/Scripts/python.exe scripts/seed_world.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session
from app.config import get_settings
from app.persistence.db import create_db_engine, init_db
from app.persistence.repository import WorldRepository, CharacterRepository, LocationRepository
from app.models.world import World
from app.models.character import Character
from app.models.location import Location


def seed():
    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    init_db(engine)

    with Session(engine) as s:
        # 创建世界
        repo_w = WorldRepository(s)
        existing = repo_w.list()
        if any(w.name == "艾尔德兰" for w in existing):
            print("艾尔德兰已存在，跳过种子。")
            return
        world = repo_w.create(World(
            name="艾尔德兰",
            vision="魔法衰落的王国",
            setting="三年前寂灭之乱后魔法急剧衰退，旧贵族死守权力，流亡者在边境集结。冬月风雪，流亡骑士归来。",
            rules=["魔法稀有，施法付代价", "暴力会被通缉", "誓言有约束力", "冬夜不收外乡人"],
            visual_style={"art_style": "电影感写实", "palette": "冷峻墨蓝"},
            clock_tick=0,
            state_flags={"war": False},
            initial_state={"opening": "流亡骑士艾伦雪夜归来", "inciting": "酒馆对峙"},
        ))
        print(f"世界创建: {world.name} (id={world.id})")

        # 创建角色
        repo_c = CharacterRepository(s)
        repo_c.create(Character(
            world_id=world.id, name="艾伦", archetype="流亡骑士",
            personality={"neuroticism": 0.8, "conscientiousness": 0.7, "openness": 0.4},
            backstory="曾是王国骑士，三年前被凯尔设局陷害而流亡北境。今夜归来寻仇。",
            skills=["剑术", "生存", "骑术"],
            goals={"short_term": "质问贝拉", "long_term": "揭露凯尔的阴谋"},
            state={"location_id": "断刃酒馆", "health": 100, "mood": "愤怒"},
        ))
        repo_c.create(Character(
            world_id=world.id, name="贝拉", archetype="酒馆老板娘",
            personality={"agreeableness": 0.6, "neuroticism": 0.7},
            backstory="艾伦旧爱，三年前被凯尔威胁而背叛艾伦。经营寒鸦镇「断刃」酒馆。",
            skills=["人脉", "机敏", "隐忍"],
            goals={"short_term": "守住秘密", "long_term": "保护孩子"},
            state={"location_id": "断刃酒馆", "health": 90, "mood": "恐惧"},
        ))
        repo_c.create(Character(
            world_id=world.id, name="凯尔", archetype="宫廷谋士",
            personality={"machiavellianism": 0.9, "emotional_stability": 0.8},
            backstory="王国实际操盘者，三年前设局清除异己。在王城谋士塔运筹帷幄。",
            skills=["权术", "冷酷", "耐心"],
            goals={"short_term": "观望", "long_term": "让王国在内乱中重建秩序"},
            state={"location_id": "谋士塔", "health": 100, "mood": "平静"},
        ))
        print(f"角色创建: 艾伦、贝拉、凯尔")

        # 创建地点
        repo_l = LocationRepository(s)
        for name in ["断刃酒馆", "寒鸦镇集市", "王城谋士塔", "北境营地", "雪松林神殿"]:
            repo_l.create(Location(world_id=world.id, name=name))
        print(f"地点创建: 5 个")

        print(f"\n种子完成！世界 ID: {world.id}")
        print(f"启动模拟: POST /worlds/{world.id}/simulate/start")
        print(f"推进: POST /worlds/{world.id}/simulate/step")


if __name__ == "__main__":
    seed()
