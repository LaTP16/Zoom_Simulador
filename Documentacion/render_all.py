import os
from plantuml import PlantUML

base_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(base_dir, 'imagenes')
os.makedirs(output_dir, exist_ok=True)

server = PlantUML(url='http://www.plantuml.com/plantuml/img/')

diagrams = {
    'entidad_relacion.puml': 'Entidad-Relacion.png',
    'clases.puml': 'clases.png',
    'secuencia.puml': 'secuencia.png',
    'flujo_ejecucion.puml': 'flujo_ejecucion.png'
}

for src_name, dest_name in diagrams.items():
    src_path = os.path.join(base_dir, src_name)
    dest_path = os.path.join(output_dir, dest_name)
    
    if os.path.exists(src_path):
        print(f"Rendering {src_name} -> {dest_name}...")
        try:
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            img_data = server.processes(content)
            with open(dest_path, 'wb') as f:
                f.write(img_data)
            print(f"Success! Generated {dest_name} ({len(img_data)} bytes)")
        except Exception as e:
            print(f"Error rendering {src_name}: {e}")
    else:
        print(f"File not found: {src_path}")
