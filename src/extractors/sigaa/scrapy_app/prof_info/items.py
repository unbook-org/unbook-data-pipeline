# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from dataclasses import dataclass


@dataclass
class ProfinfoItem:
    nome: str
    departamento: str

@dataclass
class TurmaItem:
    course_code: str
    course_name: str
    class_code: str
    schedules_raw: str
    location: str
    vacancies: int
    docente: str
    departamento: str