import requests, json, re
from bs4 import BeautifulSoup

def get_assignments():
    cookies = {c['name']: c['value'] for c in json.load(open('cookies.json'))}
    soup = BeautifulSoup(requests.get("https://psu.instructure.com/courses/2404351/grades", cookies=cookies).text, 'lxml')
    
    assignments = [{
        'name': row.find('a').text.strip(),
        'category': row.find('div', class_='context').text.strip(),
        'due_date': row.find('td', class_='due').text.strip(),
        'score': f"{[t for t in row.find('span', class_='grade').stripped_strings][-1] if row.find('span', class_='grade') else '-'}/{row.find('span', class_='grade').find_next_sibling('span').text.strip('/ ') if row.find('span', class_='grade') else '0'}",
        'link': re.sub(r'/submissions/\d+$', '', row.find('a').get('href', ''))
    } for row in soup.find_all('tr', class_='student_assignment') if not {'group_total', 'final_grade'} & set(row.get('class', []))]
    
    json.dump(assignments, open('assignments.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return assignments

if __name__ == '__main__':
    get_assignments()