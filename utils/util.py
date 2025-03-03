


def read_txt_file_to_list(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            records.append(line.strip())
    return records