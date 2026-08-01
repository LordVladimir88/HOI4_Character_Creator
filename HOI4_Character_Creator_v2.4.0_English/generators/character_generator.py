from __future__ import annotations

from dataclasses import dataclass, field


def format_traits(raw_traits: str) -> str:
    traits = [trait.strip() for trait in raw_traits.split(",") if trait.strip()]
    return "{ " + " ".join(traits) + " }" if traits else "{ }"


def indent(text: str, level: int = 1) -> str:
    prefix = "    " * level
    return "\n".join(prefix + line if line else "" for line in text.splitlines())


@dataclass
class LeaderData:
    enabled: bool = False
    ideology: str = "paternal_despotism"
    traits: str = ""
    expire: str = "1965.1.1"
    description: str = ""


@dataclass
class MilitaryData:
    enabled: bool = False
    role: str = "corps_commander"
    traits: str = ""
    skill: int = 1
    attack: int = 1
    defense: int = 1
    planning: int = 1
    logistics: int = 1


@dataclass
class AdvisorData:
    enabled: bool = False
    slot: str = "army_chief"
    idea_token: str = ""
    traits: str = ""
    cost: int = 100


@dataclass
class CharacterData:
    tag: str
    identifier: str
    name_key: str
    portrait_key: str
    display_name: str = ""
    portrait_source: str = ""
    leader: LeaderData = field(default_factory=LeaderData)
    military: MilitaryData = field(default_factory=MilitaryData)
    advisor: AdvisorData = field(default_factory=AdvisorData)

    @property
    def character_key(self) -> str:
        return f"{self.tag.upper()}_{self.identifier.lower()}"

    @property
    def roles(self) -> list[str]:
        roles: list[str] = []
        if self.leader.enabled:
            roles.append("Chef du pays")
        if self.military.enabled:
            roles.append(self.military.role)
        if self.advisor.enabled:
            roles.append(self.advisor.slot)
        return roles


class CharacterGenerator:
    def generate_country_leader(self, data: LeaderData) -> str:
        lines = [
            "country_leader = {",
            f"    ideology = {data.ideology}",
            f"    traits = {format_traits(data.traits)}",
            f'    expire = "{data.expire or "1965.1.1"}"',
            "    id = -1",
        ]

        if data.description.strip():
            lines.append(f"    desc = {data.description.strip()}")

        lines.append("}")
        return "\n".join(lines)

    def generate_military(self, data: MilitaryData) -> str:
        if data.role == "navy_leader":
            return f"""navy_leader = {{
    traits = {format_traits(data.traits)}
    skill = {data.skill}
    attack_skill = {data.attack}
    defense_skill = {data.defense}
    maneuvering_skill = {data.planning}
    coordination_skill = {data.logistics}
    legacy_id = -1
}}"""

        return f"""{data.role} = {{
    traits = {format_traits(data.traits)}
    skill = {data.skill}
    attack_skill = {data.attack}
    defense_skill = {data.defense}
    planning_skill = {data.planning}
    logistics_skill = {data.logistics}
    legacy_id = -1
}}"""

    def generate_advisor(self, data: AdvisorData) -> str:
        return f"""advisor = {{
    slot = {data.slot}
    idea_token = {data.idea_token}
    allowed = {{
        original_tag = ROOT
    }}
    traits = {format_traits(data.traits)}
    cost = {data.cost}
}}"""

    def generate_character(self, data: CharacterData) -> str:
        blocks: list[str] = []

        if data.leader.enabled:
            blocks.append(self.generate_country_leader(data.leader))

        if data.military.enabled:
            blocks.append(self.generate_military(data.military))

        if data.advisor.enabled:
            blocks.append(self.generate_advisor(data.advisor))

        body = "\n\n".join(indent(block) for block in blocks)
        if body:
            body = "\n\n" + body

        return f"""{data.character_key} = {{
    name = {data.name_key}

    portraits = {{
        civilian = {{
            large = {data.portrait_key}
        }}
    }}{body}
}}
"""

    def generate_characters_file(self, characters: list[CharacterData]) -> str:
        return "\n\n".join(
            self.generate_character(character).rstrip()
            for character in characters
        ) + "\n"

    def generate_localisation(self, data: CharacterData) -> str:
        display_name = data.display_name.strip() or data.character_key
        return f' {data.name_key}:0 "{display_name}"\n'

    def generate_localisation_file(self, characters: list[CharacterData]) -> str:
        return "\ufeffl_english:\n" + "".join(
            self.generate_localisation(character)
            for character in characters
        )

    @staticmethod
    def generate_sprite_file(entries: list[tuple[str, str]]) -> str:
        lines = ["spriteTypes = {"]

        for gfx_key, texture_path in entries:
            lines.extend(
                [
                    "    spriteType = {",
                    f'        name = "{gfx_key}"',
                    f'        texturefile = "{texture_path}"',
                    "    }",
                    "",
                ]
            )

        lines.append("}")
        return "\n".join(lines) + "\n"
