#!/usr/bin/env python3
"""
SEC EDGAR Enhanced Provider Demo
Demonstrates the new Phase 1 and Phase 2 capabilities for finance research
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.test')

from aiecs.tools.apisource import APISourceTool

def main():
    """Demonstrate SEC EDGAR enhanced capabilities"""
    
    print("\n" + "="*80)
    print("SEC EDGAR Enhanced Provider Demo")
    print("="*80)
    
    # Initialize APISource Tool
    config = {
        'secedgar_config': {
            'user_agent': os.getenv('SECEDGAR_USER_AGENT', 'Demo demo@example.com'),
            'timeout': 30,
            'rate_limit': 10,
        }
    }
    
    tool = APISourceTool(config)
    print("✓ APISource Tool initialized\n")
    
    # Company to analyze: Apple Inc.
    cik = '0000320193'
    company_name = "Apple Inc."
    
    # =========================================================================
    # Phase 1: Filing Document Operations
    # =========================================================================
    
    print("="*80)
    print("PHASE 1: Filing Document Operations")
    print("="*80 + "\n")
    
    # 1. Search for 10-K filings
    print(f"1. Searching for {company_name} 10-K filings...")
    result = tool.query(
        provider='secedgar',
        operation='search_filings',
        params={
            'cik': cik,
            'form_type': '10-K',
            'limit': 3
        }
    )
    
    filings = result['data']['filings']
    print(f"   Found {len(filings)} 10-K filings")
    if filings:
        latest = filings[0]
        print(f"   Latest: {latest['formType']} filed on {latest['filingDate']}")
        print(f"   Accession: {latest['accessionNumber']}\n")
    
    # 2. Get filings by type (10-Q quarterly reports)
    print(f"2. Getting {company_name} 10-Q filings...")
    result = tool.query(
        provider='secedgar',
        operation='get_filings_by_type',
        params={
            'cik': cik,
            'form_type': '10-Q',
            'count': 4
        }
    )
    
    quarterly_filings = result['data']['filings']
    print(f"   Found {len(quarterly_filings)} 10-Q filings")
    for filing in quarterly_filings[:2]:
        print(f"   - {filing['formType']}: {filing['filingDate']}")
    print()
    
    # 3. Get filing documents metadata
    if filings:
        accession_number = filings[0]['accessionNumber']
        print(f"3. Getting filing documents for {accession_number}...")
        result = tool.query(
            provider='secedgar',
            operation='get_filing_documents',
            params={
                'cik': cik,
                'accession_number': accession_number
            }
        )
        
        if 'error' not in result['data']:
            doc_data = result['data']
            print(f"   Form Type: {doc_data.get('formType')}")
            print(f"   Primary Document: {doc_data.get('primaryDocument')}")
            print(f"   Document URL: {doc_data.get('primaryDocumentUrl')}")
            print(f"   Index URL: {doc_data.get('indexUrl')}\n")
    
    # =========================================================================
    # Phase 2: Financial Analysis Operations
    # =========================================================================
    
    print("="*80)
    print("PHASE 2: Financial Analysis Operations")
    print("="*80 + "\n")
    
    # 4. Calculate financial ratios
    print(f"4. Calculating financial ratios for {company_name}...")
    result = tool.query(
        provider='secedgar',
        operation='calculate_financial_ratios',
        params={'cik': cik}
    )
    
    ratios = result['data']['ratios']
    raw_values = result['data']['raw_values']
    
    print(f"   Financial Ratios:")
    if 'current_ratio' in ratios:
        print(f"   - Current Ratio: {ratios['current_ratio']:.2f}")
    if 'debt_to_equity' in ratios:
        print(f"   - Debt-to-Equity: {ratios['debt_to_equity']:.2f}")
    if 'profit_margin' in ratios:
        print(f"   - Profit Margin: {ratios['profit_margin']:.2%}")
    if 'return_on_assets' in ratios:
        print(f"   - Return on Assets (ROA): {ratios['return_on_assets']:.2%}")
    if 'return_on_equity' in ratios:
        print(f"   - Return on Equity (ROE): {ratios['return_on_equity']:.2%}")
    
    print(f"\n   Raw Values:")
    if raw_values.get('assets'):
        print(f"   - Total Assets: ${raw_values['assets']:,.0f}")
    if raw_values.get('revenue'):
        print(f"   - Revenue: ${raw_values['revenue']:,.0f}")
    if raw_values.get('net_income'):
        print(f"   - Net Income: ${raw_values['net_income']:,.0f}")
    print()
    
    # 5. Get formatted balance sheet
    print(f"5. Getting balance sheet for {company_name}...")
    result = tool.query(
        provider='secedgar',
        operation='get_financial_statement',
        params={
            'cik': cik,
            'statement_type': 'balance_sheet',
            'period': 'annual'
        }
    )
    
    line_items = result['data']['line_items']
    print(f"   Balance Sheet Items: {len(line_items)}")
    
    # Show key items
    key_items = ['Assets', 'Liabilities', 'StockholdersEquity']
    for item in key_items:
        if item in line_items:
            value = line_items[item]['value']
            date = line_items[item]['end_date']
            print(f"   - {item}: ${value:,.0f} (as of {date})")
    print()
    
    # 6. Get insider transactions
    print(f"6. Getting insider transactions for {company_name}...")
    result = tool.query(
        provider='secedgar',
        operation='get_insider_transactions',
        params={'cik': cik}
    )
    
    transactions = result['data']['insider_transactions']
    count = result['data']['count']
    
    print(f"   Found {count} Form 4 filings (insider transactions)")
    if transactions:
        print(f"   Recent transactions:")
        for txn in transactions[:3]:
            print(f"   - {txn['formType']}: {txn['filingDate']}")
    print()
    
    # =========================================================================
    # Summary
    # =========================================================================
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✓ Successfully demonstrated all enhanced SEC EDGAR capabilities")
    print(f"✓ Phase 1: Filing document access and search")
    print(f"✓ Phase 2: Financial analysis and insider transactions")
    print(f"\nThe SEC EDGAR provider now supports comprehensive finance research!")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()

