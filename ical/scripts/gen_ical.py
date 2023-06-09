import mkdocs_gen_files
import icalendar
from icalendar import vText
from rdflib import Graph
from datetime import datetime
from pytz import timezone

from urllib import parse
from os import path
class FileMapper:
    def __init__(self, config, mkdocs_gen_files_ref=None):
        self.base_iri = parse.urlparse(config["base_iri"])
        self.default_suffix = config["default_suffix"] or ".md"
        self.mkdocs_gen_files = mkdocs_gen_files_ref or mkdocs_gen_files

    def iri_to_file(self, iri, suffix=None):
        if suffix is None:
            suffix = self.default_suffix
        iri_parsed = parse.urlparse(iri)

        if self.base_iri.path == path.commonpath([self.base_iri.path, iri_parsed.path]):
            iri_relpath = iri_parsed.path[len(self.base_iri.path):]
            (head, tail) = path.split(iri_relpath)
            if tail == "":
                tail = "index"
            else:
                (tail, ext) = path.splitext(tail)
            mkdocs_path = path.join(head, tail + suffix)
            if not mkdocs_path in self.mkdocs_gen_files.files:
                with mkdocs_gen_files.open(mkdocs_path, "w") as f:
                    print("", file=f)
            return self.mkdocs_gen_files.files.get_file_from_path(mkdocs_path)
        return False


g = Graph()

fm = FileMapper(config={
    "base_iri": "https://2023.dataweek.de/",
    "default_suffix": ".ics"
})

# Query the graph for event data using SPARQL
query = """
PREFIX schema: <http://schema.org/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?event (min(?date_) as ?date) (min(?start_) as ?start) (max(?end_) as ?end) (min(?title_) as ?title) (min(?description_) as ?description) (min(?location_) as ?location)
WHERE {
  ?event a schema:Event ;
         dct:date ?date_ ;
         schema:startTime ?start_ ;
         schema:endTime ?end_ ;
         schema:location ?loc ;
         dct:title ?dcttitle_ .
  optional {
    ?event skos:prefLabel ?prefLabel_ .
    filter(langMatches(lang(?prefLabel_), "en"))
  }
  ?loc dct:title ?location_ .
         filter(langMatches(lang(?dcttitle_), "en"))
         filter(langMatches(lang(?location_), "en"))
         bind (coalesce(?prefLabel_, ?dcttitle_) as ?title_)
  optional {
    ?event dct:description ?description_ .
    filter(langMatches(lang(?description_), "en"))
  }
}
group by ?event
order by ?date
"""
# Load the Graph
g.parse("data/graph.nt")

results = g.query(query)

# Create an iCalendar object and add event data to it
cal = icalendar.Calendar()
events = {}
days = {}
for row in results:
    date = row.date.toPython()
    if not row.date in days:
        days[row.date] = icalendar.Calendar()
    start = datetime.combine(date, row.start.toPython(), timezone("Europe/Berlin"))
    end = datetime.combine(date, row.end.toPython(), timezone("Europe/Berlin"))
    event = icalendar.Event()
    event.add('summary', row.title)
    event.add('dtstart', start)
    event.add('dtend', end)
    if row.description is not None:
        event.add('description', row.description)
    event.add('location', vText(row.location))
    cal.add_component(event)
    days[row.date].add_component(event)
    events[row.event] = event

# Write the iCalendar object to a file
with mkdocs_gen_files.open("index.ics", "wb") as f:
    f.write(cal.to_ical())

for day in days:
    file = fm.iri_to_file("https://2023.dataweek.de/" + day + "/")
    with mkdocs_gen_files.open(file.src_uri, "wb") as f:
        f.write(days[day].to_ical())
