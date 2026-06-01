from sqlalchemy.orm import Session

from backend.research.models import ResearchProfile
from backend.research.schemas import ResearchProfileUpdate


DEFAULT_PROFILE_ID = "default"


class ResearchProfileService:
    def __init__(self, session: Session):
        self.session = session

    def get_profile(self) -> ResearchProfile | None:
        return self.session.get(ResearchProfile, DEFAULT_PROFILE_ID)

    def update_profile(self, payload: ResearchProfileUpdate) -> ResearchProfile:
        profile = self.get_profile()
        if profile is None:
            profile = ResearchProfile(id=DEFAULT_PROFILE_ID)
            self.session.add(profile)
        profile.name = payload.name or "Default Research Profile"
        profile.primary_domains_json = payload.primary_domains
        profile.active_questions_json = payload.active_questions
        profile.target_venues_json = payload.target_venues
        profile.methodological_preferences_json = payload.methodological_preferences
        profile.resource_constraints_json = payload.resource_constraints
        profile.risk_tolerance = payload.risk_tolerance or "medium"
        profile.timeline_horizon = payload.timeline_horizon
        profile.negative_preferences_json = payload.negative_preferences
        profile.evaluation_weights_json = {
            key: float(value) for key, value in payload.evaluation_weights.items() if value > 0
        }
        profile.notes = payload.notes
        profile.created_by = payload.created_by or "researcher"
        profile.markdown_export = render_research_profile_markdown(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile


def default_research_profile_markdown() -> str:
    lines = [
        "# Research Profile: Default Research Profile",
        "",
        "- Profile ID: `default`",
        "- Risk Tolerance: medium",
        "",
        "## Primary Domains",
        "",
        "- Not specified.",
        "",
        "## Active Questions",
        "",
        "- Not specified.",
        "",
        "## Constraints",
        "",
        "- Not specified.",
        "",
    ]
    return "\n".join(lines)


def render_research_profile_markdown(profile: ResearchProfile) -> str:
    lines = [
        f"# Research Profile: {profile.name}",
        "",
        f"- Profile ID: `{profile.id}`",
        f"- Created By: {profile.created_by}",
        f"- Risk Tolerance: {profile.risk_tolerance}",
        f"- Timeline Horizon: {profile.timeline_horizon or 'not specified'}",
        "",
    ]
    lines.extend(_render_list("Primary Domains", profile.primary_domains_json or []))
    lines.extend(_render_list("Active Questions", profile.active_questions_json or []))
    lines.extend(_render_list("Target Venues", profile.target_venues_json or []))
    lines.extend(
        _render_list(
            "Methodological Preferences",
            profile.methodological_preferences_json or [],
        )
    )
    lines.extend(_render_list("Resource Constraints", profile.resource_constraints_json or []))
    lines.extend(_render_list("Negative Preferences", profile.negative_preferences_json or []))
    lines.extend(["", "## Evaluation Weights", ""])
    if profile.evaluation_weights_json:
        for key, value in profile.evaluation_weights_json.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- Default ranking weights.")
    lines.extend(["", "## Notes", "", profile.notes or "Not specified."])
    return "\n".join(lines).strip() + "\n"


def _render_list(title: str, items: list[str]) -> list[str]:
    lines = ["", f"## {title}", ""]
    if not items:
        return lines + ["- Not specified."]
    return lines + [f"- {item}" for item in items]
