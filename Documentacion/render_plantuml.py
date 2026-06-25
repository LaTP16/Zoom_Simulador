from plantuml import PlantUML
import os

puml_file = r'C:\Users\User\Desktop\LP\PC3POO\Documentacion\casos_de_uso.puml'
output_dir = r'C:\Users\User\Desktop\LP\PC3POO\Documentacion\imagenes'
output_file = os.path.join(output_dir, 'casos_de_uso.png')

os.makedirs(output_dir, exist_ok=True)

server = PlantUML(url='http://www.plantuml.com/plantuml/img/')
with open(puml_file, 'r', encoding='utf-8') as f:
    content = f.read()
img_data = server.processes(content)
with open(output_file, 'wb') as f:
    f.write(img_data)
print(f"Diagram generated: {output_file} ({len(img_data)} bytes)")
