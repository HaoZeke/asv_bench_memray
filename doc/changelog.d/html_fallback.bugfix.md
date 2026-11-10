The memray HTML report no longer turns every exception into a stub page.
A missing flamegraph reporter still writes a stub that names the import
error. Any other failure is reported, and a partial HTML file is removed.
