import mkdocs_gen_files
import icalendar
from icalendar import vText
from rdflib import Graph
from datetime import datetime
from pytz import timezone

g = Graph()

# Query the graph for event data using SPARQL
query = """
PREFIX schema: <http://schema.org/>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT ?event ?date ?start ?end ?title ?description ?location
WHERE {
  ?event a schema:Event ;
         dct:date ?date ;
         schema:startTime ?start ;
         schema:endTime ?end ;
         schema:location ?loc ;
         dct:title ?title .
  ?loc dct:title ?location .
         filter(langMatches(lang(?title), "en"))
         filter(langMatches(lang(?location), "en"))
  optional {
    ?event dct:description ?description .
    filter(langMatches(lang(?description), "en"))
  }
}
"""
# Load the Graph
g.parse("data/graph.nt")

results = g.query(query)

# Create an iCalendar object and add event data to it
cal = icalendar.Calendar()
days = {}
for row in results:
    date = row.date.toPython()
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
    days[row.event] = event

# Write the iCalendar object to a file
with mkdocs_gen_files.open("leipzig-dataweek.ics", "wb") as f:
    f.write(cal.to_ical())

with mkdocs_gen_files.open("hallo.ics", "w") as f:
    print("<strong>Hello, world!</strong>", file=f)
