"""Modelos Pydantic do schema processado de currículos (docs/sigaa_curriculos_SPEC.md)."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

SOURCE_URL = "https://sigaa.unb.br/sigaa/public/curso/curriculo.jsf"

Nature = Literal["obrigatoria", "optativa"]
Status = Literal["ativa", "inativa"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Component(_StrictModel):
    course_code: str = Field(min_length=1)
    course_name: str = Field(min_length=1)
    workload_hours: int = Field(ge=0)
    nature: Nature
    level: int | None = Field(default=None, ge=1)
    prerequisites_raw: str | None = None

    @model_validator(mode="after")
    def _level_only_for_mandatory(self) -> "Component":
        if self.nature == "obrigatoria" and self.level is None:
            raise ValueError("componente obrigatório exige 'level' inteiro")
        if self.nature == "optativa" and self.level is not None:
            raise ValueError("componente optativo deve ter 'level' nulo")
        return self


class Workload(_StrictModel):
    total_hours: int | None = None
    optional_min_hours: int | None = None
    complementary_min_hours: int | None = None
    elective_max_hours: int | None = None
    max_hours_per_term: int | None = None
    min_hours_per_term: int | None = None


class CompletionSemesters(_StrictModel):
    min: int | None = None
    avg: int | None = None
    max: int | None = None


class Curriculum(_StrictModel):
    curriculum_code: str = Field(min_length=1)
    created_year: int
    status: Status
    shift_group: str | None = None
    workload: Workload
    completion_semesters: CompletionSemesters
    components: list[Component]


class Program(_StrictModel):
    sigaa_program_id: str = Field(min_length=1)
    name: str
    degree: str
    shift: str
    unit: str
    city: str
    modality: str
    curricula: list[Curriculum]


class CurriculaOutput(_StrictModel):
    source: str = SOURCE_URL
    extracted_at: AwareDatetime
    programs: list[Program]
