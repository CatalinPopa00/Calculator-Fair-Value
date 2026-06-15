from scraper.yahoo import get_company_data, generate_synthesis
data = get_company_data('ADBE')
synthesis = generate_synthesis(data)
print(synthesis)
