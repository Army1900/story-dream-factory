from dataclasses import dataclass, field


@dataclass
class TierConfig:
    model: str
    fallback_models: list[str] = field(default_factory=list)


@dataclass
class LLMRoutingConfig:
    tiers: dict[str, TierConfig]
    default_tier: str = "tier1"

    def models_for_tier(self, tier: str) -> list[str]:
        t = self.tiers.get(tier) or self.tiers[self.default_tier]
        return [t.model, *t.fallback_models]
