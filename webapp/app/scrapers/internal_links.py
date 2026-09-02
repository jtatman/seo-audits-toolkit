from urllib.parse import urljoin, urlparse

import networkx as nx
from bokeh.embed import json_item
from bokeh.models import HoverTool, MultiLine, Scatter
from bokeh.palettes import Viridis256
from bokeh.plotting import figure, from_networkx
from bokeh.transform import linear_cmap

from .http_tools import request_parse

MAX_PAGES = 200


def _crawl(start_url, max_pages):
    """Breadth-first same-domain crawl, building {path: [linked paths]}."""
    domain = urlparse(start_url).netloc
    graph = {}
    queue = [start_url]
    seen = {start_url}

    while queue and len(graph) < max_pages:
        url = queue.pop(0)
        soup = request_parse(url)
        if soup is None:
            continue

        links = []
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue
            full_url = urljoin(url, href).split("#")[0]
            if urlparse(full_url).netloc != domain:
                continue
            links.append(full_url)
            if full_url not in seen and len(seen) < max_pages:
                seen.add(full_url)
                queue.append(full_url)

        graph[url] = links

    return graph


def generate_graph(start_url, maximum=MAX_PAGES):
    graph = _crawl(start_url, maximum)
    if not graph:
        raise RuntimeError(f"Could not fetch {start_url}")

    g = nx.Graph()
    for page, links in graph.items():
        for link in links:
            if link in graph:  # only draw edges to pages we actually visited
                g.add_edge(page, link)
    if g.number_of_nodes() == 0:
        g.add_node(start_url)

    degrees = dict(g.degree())
    nx.set_node_attributes(g, degrees, "degree")
    max_degree = max(degrees.values()) if degrees else 1
    # guard against an all-zero-degree graph (a page with no internal links
    # found at all) so the color scale doesn't divide by zero
    max_degree = max(max_degree, 1)

    plot = figure(
        width=800,
        height=800,
        tools="pan,wheel_zoom,save,reset",
        toolbar_location="above",
        x_range=(-1.2, 1.2),
        y_range=(-1.2, 1.2),
    )
    graph_renderer = from_networkx(g, nx.spring_layout, scale=1, center=(0, 0))
    graph_renderer.node_renderer.glyph = Scatter(
        size=15, fill_color=linear_cmap("degree", Viridis256, 0, max_degree)
    )
    graph_renderer.edge_renderer.glyph = MultiLine(
        line_color="#cccccc", line_alpha=0.6
    )
    plot.renderers.append(graph_renderer)
    plot.add_tools(HoverTool(tooltips=[("page", "@index"), ("links", "@degree")]))

    return {
        "pages_crawled": len(graph),
        "total_links": sum(len(v) for v in graph.values()),
        "bokeh_item": json_item(plot, "internal-links-graph"),
    }
