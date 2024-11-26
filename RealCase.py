import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import folium
from folium import plugins
import random

def create_network_with_basemap(center_lat=39.9332, 
                              center_lon=116.4554, 
                              dist=500,
                              network_type='drive',
                              num_task_edges=20):

    ox.config(use_cache=True, log_console=True)
    ox.settings.default_language = 'en'
    
    G = ox.graph_from_point((center_lat, center_lon), 
                           dist=dist,
                           network_type=network_type,
                           simplify=True)

    G = ox.utils_graph.get_undirected(G)
    
    print(f"Number of nodes: {len(G.nodes)}")
    print(f"Number of edges: {len(G.edges)}")
    
    m = folium.Map(location=[center_lat, center_lon], 
                  zoom_start=16,
                  tiles=None)

    folium.TileLayer(
        tiles='http://wprd04.is.autonavi.com/appmaptile?lang=en&size=1&scale=1&style=7&x={x}&y={y}&z={z}',
        attr='© AutoNavi',
        name='AMap English',
        control=True, 
        opacity=0.3
    ).add_to(m)

    for node, data in G.nodes(data=True):
        folium.CircleMarker(
            location=(data['y'], data['x']),
            radius=6,
            color='#D92121',
            weight=2,
            fill=True,
            fill_color='#FF4444',
            fill_opacity=0.9,
            popup=f"""
            <div style='font-family: Arial, sans-serif;'>
                <b>Node Information</b><br>
                ID: {node}<br>
                Latitude: {data['y']:.4f}<br>
                Longitude: {data['x']:.4f}
            </div>
            """,
            tooltip=f'Node {node}'
        ).add_to(m)
    
    all_edges = list(G.edges(data=True))

    sorted_edges = sorted(all_edges, key=lambda x: x[2].get('length', 0), reverse=True)
    candidate_edges = sorted_edges[:len(sorted_edges)//2]
    task_edges = random.sample(candidate_edges, min(num_task_edges, len(candidate_edges)))
    task_edge_pairs = set((u, v) for u, v, _ in task_edges)

    for u, v, data in G.edges(data=True):
        coords = [(G.nodes[u]['y'], G.nodes[u]['x']),
                 (G.nodes[v]['y'], G.nodes[v]['x'])]
        
        is_task_edge = (u, v) in task_edge_pairs or (v, u) in task_edge_pairs

        if is_task_edge:
            color = '#FF0000'  
            weight = 4.0      
            opacity = 0.9     
            edge_type = "Task Edge"
        else:
            color = '#7B98E5' 
            weight = 3.0  
            opacity = 0.6 
            edge_type = "Normal Edge"

        folium.PolyLine(
            coords,
            weight=weight,
            color=color,
            opacity=opacity,
            popup=f"""
            <div style='font-family: Arial, sans-serif;'>
                <b>{edge_type}</b><br>
                Length: {int(data.get('length', 0))}m
            </div>
            """,
            tooltip=f'Click for details'
        ).add_to(m)

    legend_html = '''
    <div style="
        position: fixed; 
        bottom: 50px; 
        right: 50px; 
        width: 180px; 
        height: 120px; 
        border:2px solid grey; 
        z-index:9999; 
        background-color:white;
        opacity:0.8;
        font-family: Arial, sans-serif;
        font-size:12px;
        padding:10px">
        <b>Network Legend</b><br>
        <i class="fa fa-circle" style="color:#FF4444"></i> Nodes<br>
        <i class="fa fa-minus" style="color:#7B98E5"></i> Normal Roads<br>
        <i class="fa fa-minus" style="color:#FF0000"></i> Task Roads
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    plugins.Fullscreen().add_to(m)

    minimap = plugins.MiniMap(zoom_level_offset=-5)
    m.add_child(minimap)

    m.save('network_map.html')
    
    return G, m, task_edge_pairs

def adjust_network_size(G, target_nodes=100):

    if G.is_directed():
        G = G.to_undirected()
    
    largest_cc = max(nx.connected_components(G), key=len)
    G = G.subgraph(largest_cc).copy()
    
    while len(G.nodes) > target_nodes:
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(G, nodes=True, edges=True)
        G = ox.graph_from_gdfs(nodes_gdf, edges_gdf)
        
        if len(G.nodes) > target_nodes:
            edges = list(G.edges())
            for edge in edges:
                if len(G.nodes) <= target_nodes:
                    break
                G.remove_edge(*edge)
                if not nx.is_connected(G.to_undirected()):
                    G.add_edge(*edge)
    
    return G

def export_network_to_json_format(G, task_edge_pairs):

    node_to_index = {node: i for i, node in enumerate(G.nodes())}

    node_coords = []
    for node in G.nodes():
        node_coords.append([
            G.nodes[node]['x'],  # longitude
            G.nodes[node]['y']   # latitude
        ])

    edges_data = []
    for u, v, data in G.edges(data=True):
        length = int(data.get('length', 1)) 
        edges_data.append([node_to_index[u], node_to_index[v], float(length/1000)])
        edges_data.append([node_to_index[v], node_to_index[u], float(length/1000)])

    task_edges_list = [[node_to_index[u], node_to_index[v]] for u, v in task_edge_pairs]

    result = {
        "network_data": [
            node_coords,
            edges_data,
            task_edges_list
        ]
    }
    
    return result

def main():
    """
    Main function to generate and visualize the network
    """
    try:
        center_lat, center_lon = 39.9332, 116.4554
        dist = 300

        G, m, task_edges = create_network_with_basemap(center_lat, center_lon, dist)

        while len(G.nodes) < 100:
            dist += 50
            G, m, task_edges = create_network_with_basemap(center_lat, center_lon, dist)

        if len(G.nodes) > 120:
            G = adjust_network_size(G, target_nodes=100)
            G, m, task_edges = create_network_with_basemap(center_lat, center_lon, dist)
        
        print("\nFinal network statistics:")
        print(f"Number of nodes: {len(G.nodes)}")
        print(f"Number of edges: {len(G.edges)}")
        print(f"Number of task edges: {len(task_edges)}")

        json_data = export_network_to_json_format(G, task_edges)
        import json
        with open('network_data.json', 'w') as f:
            json.dump(json_data, f, indent=2)
        
        return G, m, task_edges
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return None, None, None


if __name__ == "__main__":
    G, m, task_edges = main()
