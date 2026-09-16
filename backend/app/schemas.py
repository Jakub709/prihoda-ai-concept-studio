from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Room(StrictModel):
    type: Literal['production_hall', 'warehouse', 'sports_hall'] = 'production_hall'
    length_m: float = Field(ge=5, le=100)
    width_m: float = Field(ge=5, le=60)
    height_m: float = Field(ge=3, le=20)

class Air(StrictModel):
    airflow_m3h: float | None = Field(default=None, gt=0, le=500000)
    supply_temperature_c: float | None = Field(default=None, ge=-30, le=60)
    room_temperature_c: float | None = Field(default=None, ge=-30, le=60)
    static_pressure_pa: float | None = Field(default=None, gt=0, le=3000)
    occupied_zone_velocity_ms: float | None = Field(default=None, gt=0, le=10)

class Ducts(StrictModel):
    count: int = Field(ge=1, le=8)
    shape: Literal['circular', 'semicircular'] = 'circular'
    diameter_mm: float = Field(ge=100, le=2000)
    length_m: float = Field(ge=1, le=95)
    installation_height_m: float = Field(ge=1, le=19)
    spacing_m: float = Field(ge=0.3, le=20)
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')

class Distribution(StrictModel):
    type: Literal['microperforation', 'perforation', 'small_nozzles', 'large_nozzles'] = 'large_nozzles'
    direction: Literal['horizontal', 'downward', 'angled_down'] = 'angled_down'
    angle_deg: float = Field(default=30, ge=0, le=90)

class Visualization(StrictModel):
    airflow_mode: Literal['off', 'lines', 'animated'] = 'animated'
    show_occupied_zone: bool = False
    show_dimensions: bool = True
    environment: Literal['production_hall'] = 'production_hall'

class Project(StrictModel):
    project_name: str = Field(min_length=1, max_length=100)
    original_request: str | None = Field(default=None, max_length=8000)
    room: Room
    air: Air
    ducts: Ducts
    distribution: Distribution
    visualization: Visualization = Field(default_factory=Visualization)

    @model_validator(mode='after')
    def geometry_fits(self):
        d, r = self.ducts, self.room
        radius = d.diameter_mm / 2000
        if d.length_m > r.length_m - 1:
            raise ValueError('Ducts must be at least 1 m shorter than the hall.')
        if d.installation_height_m + radius > r.height_m:
            raise ValueError('Ducts would intersect the roof. Reduce the height or diameter.')
        if (d.count - 1) * d.spacing_m + 2 * radius > r.width_m - 0.5:
            raise ValueError('The duct arrangement is wider than the hall. Reduce spacing or count.')
        if d.count > 1 and d.spacing_m <= 2 * radius:
            raise ValueError('Ducts overlap. Increase spacing or reduce diameter.')
        return self

DEMO = Project.model_validate({
    'project_name': 'Production Hall Demo',
    'room': {'type': 'production_hall', 'length_m': 30, 'width_m': 15, 'height_m': 6},
    'air': {'airflow_m3h': 7000, 'supply_temperature_c': 16, 'room_temperature_c': 22},
    'ducts': {'count': 2, 'shape': 'circular', 'diameter_mm': 600, 'length_m': 22,
              'installation_height_m': 4.5, 'spacing_m': 6, 'color': '#eeeeee'},
    'distribution': {'type': 'large_nozzles', 'direction': 'angled_down', 'angle_deg': 30},
})

class TextRequest(StrictModel):
    text: str = Field(min_length=3, max_length=8000)

class ModifyRequest(StrictModel):
    command: str = Field(min_length=3, max_length=3000)
    project: Project

class Change(StrictModel):
    path: str
    old_value: str | float | int | bool | None
    new_value: str | float | int | bool | None

class Patch(StrictModel):
    changes: list[Change] = Field(min_length=1, max_length=30)

ALLOWED_PATHS = {
    f'{section}.{field}' for section, model in [('room', Room), ('air', Air),
    ('ducts', Ducts), ('distribution', Distribution), ('visualization', Visualization)]
    for field in model.model_fields
} | {'project_name'}

def patch_response_schema():
    schema = Patch.model_json_schema()
    schema['$defs']['Change']['properties']['path']['enum'] = sorted(ALLOWED_PATHS)
    return schema

def apply_patch(project: Project, patch: Patch) -> Project:
    data = project.model_dump()
    seen = set()
    for change in patch.changes:
        if change.path not in ALLOWED_PATHS:
            raise ValueError('AI vrátila nepodporovaný parametr. Zkuste zadání zopakovat; původní projekt zůstává zachovaný.')
        if change.path in seen:
            raise ValueError('AI navrhla více změn stejného parametru. Zadejte pro každý parametr jednu výslednou hodnotu.')
        seen.add(change.path)
        if change.path == 'project_name':
            target, field = data, 'project_name'
        else:
            section, field = change.path.split('.')
            target = data[section]
        if target[field] != change.old_value:
            raise ValueError('The concept changed meanwhile. Please try the instruction again.')
        target[field] = change.new_value
    return Project.model_validate(data)
