#!/usr/bin/env python3
"""
Farsight2 Query Test Runner
This script reads questions from test_questions.csv and sends them to the Farsight2 API.
"""

import csv
import json
import time
import requests
from datetime import datetime
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/query"
RESULTS_DIR = Path("./results")
RESULTS_DIR.mkdir(exist_ok=True)

# Create a timestamp for this test run
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
results_file = RESULTS_DIR / f"query_results_{timestamp}.json"
log_file = RESULTS_DIR / f"query_log_{timestamp}.txt"

# Initialize results dictionary
results = {
    "meta": {
        "timestamp": timestamp,
        "total_questions": 0,
        "successful_queries": 0,
        "failed_queries": 0,
    },
    "queries": [],
}


def log_message(message, also_print=True):
    """Write message to log file and optionally print to console"""
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()}: {message}\n")
    if also_print:
        print(message)


def send_query(query_text):
    """Send a query to the API and return the response"""
    try:
        payload = {"query": query_text}
        headers = {"Content-Type": "application/json"}
        response = requests.post(API_URL, json=payload, headers=headers)
        return response
    except Exception as e:
        return {"error": str(e), "status_code": 0}


def main():
    """Main function to read questions and send queries"""
    log_message(f"Starting query test run at {timestamp}")
    log_message(f"Results will be saved to {results_file}")

    try:
        with open("./test_questions.csv", "r") as csvfile:
            reader = csv.DictReader(csvfile)

            for i, row in enumerate(reader, 1):
                # Extract information
                # company_ticker,company_name,year,quarter,filing_type,query,answer
                company = row["company_name"]
                ticker = row["company_ticker"]
                year = row["year"]
                quarter = row["quarter"]
                filing_type = row["filing_type"]
                query_text = row["query"]
                answer = row["answer"]
                log_message(f"Processing query {i}: {query_text}")
                log_message(
                    f"  Company: {company} ({ticker}), Year: {year}, Quarter: {quarter}, Filing: {filing_type}"
                )

                # Update statistics
                results["meta"]["total_questions"] += 1
                

                # Send the query
                try:
                    start_time = time.time()
                    response = send_query(query_text)
                    elapsed_time = time.time() - start_time

                    if (
                        hasattr(response, "status_code")
                        and 200 <= response.status_code < 300
                    ):
                        response_data = response.json()
                        log_message(
                            f"  Success: Response received in {elapsed_time:.2f} seconds"
                        )
                        results["meta"]["successful_queries"] += 1
                    else:
                        if hasattr(response, "status_code"):
                            error_message = f"HTTP {response.status_code}: {response.text if hasattr(response, 'text') else 'Unknown error'}"
                        else:
                            error_message = str(response.get("error", "Unknown error"))

                        log_message(f"  Failed: {error_message}")
                        response_data = {
                            "error": error_message,
                            "status_code": getattr(response, "status_code", 0),
                        }
                        results["meta"]["failed_queries"] += 1

                    # Save this query result
                    query_result = {
                        "query_id": i,
                        "company": company,
                        "ticker": ticker,
                        "year": year,
                        "quarter": quarter,
                        "filing_type": filing_type,
                        "query": query_text,
                        "elapsed_time": elapsed_time,
                        "successful": hasattr(response, "status_code")
                        and 200 <= response.status_code < 300,
                        "response": response_data,
                    }

                    results["queries"].append(query_result)

                except Exception as e:
                    log_message(f"  Error processing query: {str(e)}")
                    results["meta"]["failed_queries"] += 1
                    results["queries"].append(
                        {
                            "query_id": i,
                            "company": company,
                            "ticker": ticker,
                            "year": year,
                            "quarter": quarter,
                            "filing_type": filing_type,
                            "query": query_text,
                            "successful": False,
                            "error": str(e),
                        }
                    )

                # Save results after each query in case of interruption
                with open(results_file, "w") as f:
                    json.dump(results, f, indent=2)

                # Optional delay to avoid overwhelming the API
                time.sleep(4)

        # Final summary
        log_message("\nTest run completed")
        log_message(f"Total questions: {results['meta']['total_questions']}")
        log_message(f"Successful queries: {results['meta']['successful_queries']}")
        log_message(f"Failed queries: {results['meta']['failed_queries']}")
        log_message(
            f"Success rate: {(results['meta']['successful_queries'] / results['meta']['total_questions']) * 100:.2f}%"
        )
        log_message(f"Results saved to {results_file}")

    except Exception as e:
        log_message(f"Critical error in test run: {str(e)}")


if __name__ == "__main__":
    main()
