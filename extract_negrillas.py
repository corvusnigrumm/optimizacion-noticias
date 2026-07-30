import os
import re

base_dir = 'output/2026-06-03'
results = []

for folder in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, folder)
    if os.path.isdir(folder_path):
        md_file = os.path.join(folder_path, 'optimizacion-seo.md')
        if os.path.isfile(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract Negrillas
            negrillas = []
            in_negrillas = False
            for line in content.split('\n'):
                # Catch anything with 'Negrillas' in heading
                if ('Negrillas' in line and line.startswith('#')):
                    in_negrillas = True
                    continue
                if in_negrillas and line.startswith('#') and 'Negrillas' not in line:
                    break
                if in_negrillas and line.strip() != '':
                    if '**' in line:
                        # Extract the bolded part or just store the line
                        line = line.strip()
                        # If it's a numbered list item like "1. **text**", clean it
                        line = re.sub(r'^\d+\.\s*', '', line)
                        negrillas.append(line)
                
            results.append({
                'folder': folder,
                'negrillas': negrillas[:3] # Get up to 3 negrillas to keep it concise
            })

for res in results:
    print(f"---\nFolder: {res['folder']}")
    for i, neg in enumerate(res['negrillas'], 1):
        print(f"  {i}. {neg}")
