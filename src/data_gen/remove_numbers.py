import re


def clean_file(input_path, output_path):
    cleaned_lines = []
    stop_reading = False

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "## Internal Verification Functions" in line:
                break  # Stop reading and discard the rest of the file

            stripped = line.strip()

            # Skip lines that are just numbers (likely page numbers)
            if stripped.isdigit():
                continue

            # Remove numbers at the beginning of the line
            line = re.sub(r'^\d+\s*', '', line)

            # Remove the ,→ continuation marker
            #line = line.replace(',→', '').rstrip()
          
            cleaned_lines.append(line.rstrip())
        
    text = '\n'.join(cleaned_lines[1:])
    text = text.replace("\n,→", "").rstrip()
    text = text.replace("\n- **", "\n\n- **")
    text = text.replace("\n## ","\n\n\n## ")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)


domains = ['bank','dmv','library','healthcare','online_market']
for domain in domains:
	input_file = '/Users/naamazwerdling/Documents/OASB/policy_validation/orca/paper instructions/'+domain
	output_file = '/Users/naamazwerdling/Documents/OASB/policy_validation/orca/'+domain+'/policy.txt'
	clean_file(input_file, output_file)
