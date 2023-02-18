import camelot
import pdfplumber
import re
import pandas as pd

EXPECTED_SECTIONS = ['Highlights', 'General Information', 'Industries, Verticals & Keywords', 
            'Top 5 Similar Companies', 'Comparisons', 'Patents', 'Financials', 'Ownership',
          'Current Team', 'Current Board Members', 'Deal History', 'Investors', 'Lead Partners on Deals', 
          'Social Media Signals', 'Web Signals', 'Employee Signals']
EXPECTED_SECTION_ROW_KEYS = ['Top 5 Similar Companies', 'Current Team', 'Current Board Members', 'Deal History', 'Ownership', 'Investors', 'Lead Partners on Deals']
SECTION_KEYWORDS = {'Highlights': ['Highlights'], 
                    'General Information': ['Business Status', 'Ownership Status ', 'Entity Type'], 
                    'Industries, Verticals & Keywords': ['Primary Industry', 'Verticals', 'Keywords'], 
                    'Top 5 Similar Companies': ['Competitor'], 
                    'Ownership':['Ordinary', 'Person'], 
                    'Current Team': ['Cheif', 'Chief Executive' , 'Chief Technology', 'Chief Financial'], 
                    'Current Board Members': ['Board Member', 'Investment Partner'], 
                    'Deal History': ['Completed', 'Generating Revenue'], 
                   
                    'Investors': ['Minority']}

class Pitchbook_Pdf_Reader:   
    def __init__(self, file):
        self.file = file
        self.pdf = pdfplumber.open(file)
        self.num_pages = len(self.pdf.pages)
        self.data = self.get_data()
        self.pdf.close()
        
    def get_data(self):
        file_name = self.file.split('/')[-1]
        company_name = self._get_company_name()
        sections = self._get_pdf_sections()
        expected_sections = self._get_expected_sections()
        expected_section_rows = self._get_expected_section_row(sections)
        pages =  self._get_pages(expected_sections)
        has_patent = self._has_section(expected_sections, 'Patents')
        has_social_media_signals = self._has_section(expected_sections, 'Social Media Signals')
        has_web_signals = self._has_section(expected_sections, 'Web Signals')
        has_employee_signals = self._has_section(expected_sections, 'Employee Signals')
        
        highlight = self._get_section_by_name(expected_sections, 'Highlights', False)
        general_info = self._get_section_by_name(expected_sections, 'General Information', False)
        industry_info = self._get_section_by_name(expected_sections, 'Industries, Verticals & Keywords', True),
        similar_companies = self._get_section_by_name(expected_sections, 'Top 5 Similar Companies', False),
        current_team = self._get_section_by_name(expected_sections, 'Current Team', True),
        current_board_member = self._get_section_by_name(expected_sections, 'Current Board Members', True),
        deal_history = self._get_section_by_name(expected_sections, 'Deal History', True)
        #TODO CAP TABLE HISTORY check see f2 page 5
        ownership = self._get_section_by_name(expected_sections, 'Ownership', True)
        investors = self._get_section_by_name(expected_sections, 'Investors', True)

        financial = self._get_financial(expected_sections)
        
        
        data_dict = {
            'company_name': company_name,
            'file_name': file_name,
            'sections': sections,
            'expected_sections': expected_sections,
            'expected_section_rows': expected_section_rows,
            'pages': pages,
            'has_patent': has_patent,
            'has_social_media_signals': has_social_media_signals,
            'has_web_signals': has_web_signals,
            'has_employee_signals': has_employee_signals,
            'highlight': highlight,
            'general_info': general_info,
            'industry_info': industry_info,
            'similar_companies': similar_companies,
            'current_team': current_team,
            'current_board_member': current_board_member,
            'deal_history': deal_history,
            'ownership': ownership,
            'investors': investors,
            'financial': financial
        }
        
        return data_dict
    
    def _get_text_lines(self, text):
        text_lines = []
        for line in text.splitlines():
            text_lines.append(line)
        return text_lines
    
    def _get_company_name(self):
        page = self.pdf.pages[0]
        text = self._get_text_lines(page.extract_text())
        is_company_name = lambda x: 'Private Company Profile' in x
        text = list(filter(is_company_name, text))[0]
    
        company_name = text.split('|')[0].strip()
        return company_name
    
    def _get_expected_sections(self):
        num_pages = self.num_pages
        expected_sections = dict((el,None) for el in EXPECTED_SECTIONS)
    
        for i in range(0, num_pages):
            text = self.pdf.pages[i]
            text = text.filter(lambda obj: obj["object_type"] == "char" and obj["size"] >= 11)
            for section in EXPECTED_SECTIONS:
                if section in text.extract_text():
                    expected_sections[section] = i + 1
                
#         expected_sections_pages = list(set(list(filter(lambda item: item is not None, list(expected_sections.values())))))
        return expected_sections

    # get the pages start with 1 for camelot to read
    def _get_pages(self, expected_sections):
        pages = list(set(list(filter(lambda item: item is not None, list(expected_sections.values())))))
        pages = [i+1 for i in pages]
        return pages 
    
    #get list of sections found in document except Highlights
    def _get_pdf_sections(self):
        num_pages = self.num_pages
        sections_pdf = []
        for i in range(0, num_pages):
            text = self.pdf.pages[i]
            text = text.filter(lambda obj: obj["object_type"] == "char" and obj["size"] >= 11)
            sections_pdf.extend(self._get_text_lines(text.extract_text()))

        #remove page number and certain words
        removed_words = ['Generated by', 'UCL']
        sections_pdf = [ele for ele in sections_pdf if not ele.isnumeric() and not any(x in ele for x in removed_words)]

        #remove sections before 'General Information' and 'News'
        to_remove = []
        for idx, x in enumerate(sections_pdf):
            if x == 'General Information':
                to_remove.extend(list(range(0, idx)))
            if x == 'News':
                to_remove.extend(list(range(idx+1, len(sections_pdf))))

        sections_pdf = [ele for idx, ele in enumerate(sections_pdf) if idx not in to_remove]
        return sections_pdf

    def _get_expected_section_row(self, sections):
        expected_rows = dict((el,0) for el in EXPECTED_SECTION_ROW_KEYS)
    
        for section_key in EXPECTED_SECTION_ROW_KEYS:
            section = [section for section in sections if section_key in section]
            if (section is not None) and (len(section) != 0):
                expected_rows[section_key] = int(re.findall(r'\d+', section[0])[0])
        
        return expected_rows
    
    def _has_section(self, sections, expected_section):
        return True if sections.get(expected_section) is not None else False
    
    # read Financials but need to use lattice mode - that's the only table that it can read despite multiple lattice reading e.g., return 8 talbles for Chainging Health but can read only one
    def _get_financial(self, sections):
        has_financials = self._has_section(sections, 'Financials')
        if has_financials:
            page = sections.get('Financials')
            tables = camelot.read_pdf(self.file, pages=str(page),flavor='lattice')
            return tables[0].df.to_dict('records') if tables[0] is not None else None
    
    def _get_section_by_name(self, sections, section_name, has_next_page):
        has_section = self._has_section(sections, section_name)
        keywords = SECTION_KEYWORDS.get(section_name)
        if has_section:
            page = sections.get(section_name)
            tables = camelot.read_pdf(self.file, pages=str(page),flavor='stream')
            temp_df = pd.DataFrame()
            for i in range(0, tables.n):
                df = tables[i].df
                if df.applymap(lambda x: any(word in str(x) for word in keywords)).any(1).any() and not has_next_page:
                   return df.to_dict('records')
                elif df.applymap(lambda x: any(word in str(x) for word in keywords)).any(1).any():
                    temp_df = df.copy() 
            if has_next_page:
                page = sections.get(section_name) + 1
                tables = camelot.read_pdf(self.file, pages=str(page),flavor='stream')
                for i in range(0, tables.n):
                    df2 = tables[i].df
                    if df2.applymap(lambda x: any(word in str(x) for word in keywords)).any(1).any():
                        return pd.concat([temp_df, df2]).to_dict('records')
                return df.to_dict('records')
        return None
