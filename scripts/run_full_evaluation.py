"""
Master Test Runner and Evaluation Script

Runs all test suites and generates comprehensive evaluation report.
"""

import subprocess
import json
import os
import time
from datetime import datetime
from typing import Dict, Any
import sys

class TestRunner:
    """Orchestrates test execution and report generation."""
    
    def __init__(self):
        self.results_dir = "tests/results"
        os.makedirs(self.results_dir, exist_ok=True)
        self.start_time = time.time()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_suites": {},
            "summary": {},
            "metrics": {}
        }
    
    def run_test_suite(self, name: str, path: str, markers: str = None) -> Dict[str, Any]:
        """
        Run a specific test suite.
        
        Args:
            name: Test suite name
            path: Path to test file/directory
            markers: Optional pytest markers (e.g., "-m performance")
            
        Returns:
            dict: Test results
        """
        print(f"\n{'='*70}")
        print(f"Running: {name}")
        print(f"{'='*70}")
        
        cmd = ["pytest", path, "-v", "--tb=short", "--json-report", f"--json-report-file={self.results_dir}/{name}_report.json"]
        
        if markers:
            cmd.extend(markers.split())
        
        start = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start
            
            # Parse results
            report_path = f"{self.results_dir}/{name}_report.json"
            if os.path.exists(report_path):
                with open(report_path, 'r') as f:
                    report = json.load(f)
                
                return {
                    "name": name,
                    "duration": duration,
                    "passed": report.get("summary", {}).get("passed", 0),
                    "failed": report.get("summary", {}).get("failed", 0),
                    "skipped": report.get("summary", {}).get("skipped", 0),
                    "total": report.get("summary", {}).get("total", 0),
                    "success_rate": report.get("summary", {}).get("passed", 0) / max(report.get("summary", {}).get("total", 1), 1),
                    "exit_code": result.returncode
                }
            else:
                return {
                    "name": name,
                    "duration": duration,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "total": 0,
                    "success_rate": 0.0,
                    "exit_code": result.returncode,
                    "error": "Report file not found"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "name": name,
                "duration": 300,
                "passed": 0,
                "failed": 1,
                "total": 1,
                "success_rate": 0.0,
                "exit_code": -1,
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "name": name,
                "duration": time.time() - start,
                "passed": 0,
                "failed": 1,
                "total": 1,
                "success_rate": 0.0,
                "exit_code": -1,
                "error": str(e)
            }
    
    def run_all_tests(self):
        """Run all test suites in sequence."""
        print("\n" + "="*70)
        print("COMPREHENSIVE TEST SUITE EXECUTION")
        print("="*70)
        
        test_suites = [
            ("ideal_conditions", "tests/scenarios/test_ideal_conditions.py"),
            ("worst_case", "tests/scenarios/test_worst_case.py"),
            ("rag_evaluation", "tests/evaluation/test_rag_evaluation.py"),
            ("niche_logic", "tests/test_niche_logic.py"),
            ("phase1_standalone", "tests/test_phase1_standalone.py"),
        ]
        
        for name, path in test_suites:
            if os.path.exists(path):
                result = self.run_test_suite(name, path)
                self.results["test_suites"][name] = result
                
                print(f"\n✅ {name}: {result['passed']}/{result['total']} passed ({result['success_rate']*100:.1f}%)")
            else:
                print(f"\n⚠️  Skipping {name}: {path} not found")
        
        # Performance tests (if they exist)
        if os.path.exists("tests/performance"):
            result = self.run_test_suite("performance", "tests/performance", "-m performance")
            self.results["test_suites"]["performance"] = result
    
    def collect_metrics(self):
        """Collect all metrics from test runs."""
        metrics_files = [f for f in os.listdir(self.results_dir) if f.startswith("metrics_") and f.endswith(".json")]
        
        all_metrics = {}
        
        for metrics_file in metrics_files:
            try:
                with open(os.path.join(self.results_dir, metrics_file), 'r') as f:
                    data = json.load(f)
                    if "summary" in data:
                        all_metrics.update(data["summary"])
            except Exception as e:
                print(f"Warning: Could not load {metrics_file}: {e}")
        
        self.results["metrics"] = all_metrics
    
    def generate_summary(self):
        """Generate overall summary statistics."""
        total_passed = sum(r.get("passed", 0) for r in self.results["test_suites"].values())
        total_failed = sum(r.get("failed", 0) for r in self.results["test_suites"].values())
        total_skipped = sum(r.get("skipped", 0) for r in self.results["test_suites"].values())
        total_tests = sum(r.get("total", 0) for r in self.results["test_suites"].values())
        
        total_duration = time.time() - self.start_time
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "success_rate": total_passed / max(total_tests, 1),
            "total_duration_seconds": total_duration,
            "test_suites_run": len(self.results["test_suites"]),
            "all_passed": total_failed == 0
        }
    
    def generate_report(self):
        """Generate final evaluation report."""
        self.collect_metrics()
        self.generate_summary()
        
        # Save JSON report
        report_path = os.path.join(self.results_dir, "evaluation_report.json")
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate markdown report
        md_report = self.generate_markdown_report()
        md_path = os.path.join(self.results_dir, "EVALUATION_REPORT.md")
        with open(md_path, 'w') as f:
            f.write(md_report)
        
        print(f"\n{'='*70}")
        print("EVALUATION COMPLETE")
        print(f"{'='*70}")
        print(f"JSON Report: {report_path}")
        print(f"Markdown Report: {md_path}")
        print(f"\nSummary:")
        print(f"  Total Tests: {self.results['summary']['total_tests']}")
        print(f"  Passed: {self.results['summary']['total_passed']}")
        print(f"  Failed: {self.results['summary']['total_failed']}")
        print(f"  Success Rate: {self.results['summary']['success_rate']*100:.1f}%")
        print(f"  Duration: {self.results['summary']['total_duration_seconds']:.2f}s")
        
        return self.results["summary"]["all_passed"]
    
    def generate_markdown_report(self) -> str:
        """Generate markdown evaluation report."""
        md = f"""# VoiceNoteAPI Evaluation Report

**Generated:** {self.results['timestamp']}  
**Duration:** {self.results['summary']['total_duration_seconds']:.2f} seconds

## Executive Summary

- **Total Tests:** {self.results['summary']['total_tests']}
- **Passed:** {self.results['summary']['total_passed']} ✅
- **Failed:** {self.results['summary']['total_failed']} ❌
- **Skipped:** {self.results['summary']['total_skipped']} ⏭️
- **Success Rate:** {self.results['summary']['success_rate']*100:.1f}%

## Test Suite Results

"""
        
        for name, result in self.results['test_suites'].items():
            status = "✅ PASSED" if result.get('exit_code', 1) == 0 else "❌ FAILED"
            md += f"""### {name.replace('_', ' ').title()} {status}

- **Tests:** {result.get('total', 0)}
- **Passed:** {result.get('passed', 0)}
- **Failed:** {result.get('failed', 0)}
- **Duration:** {result.get('duration', 0):.2f}s
- **Success Rate:** {result.get('success_rate', 0)*100:.1f}%

"""
        
        if self.results['metrics']:
            md += "\n## Performance Metrics\n\n"
            for metric_name, metric_data in sorted(self.results['metrics'].items()):
                if isinstance(metric_data, dict):
                    md += f"### {metric_name}\n\n"
                    md += f"- **Mean:** {metric_data.get('mean', 0):.4f} {metric_data.get('unit', '')}\n"
                    md += f"- **Min:** {metric_data.get('min', 0):.4f}\n"
                    md += f"- **Max:** {metric_data.get('max', 0):.4f}\n"
                    md += f"- **Count:** {metric_data.get('count', 0)}\n\n"
        
        md += f"""
## Conclusion

{'✅ All tests passed! System is ready for deployment.' if self.results['summary']['all_passed'] else '❌ Some tests failed. Review failures before deployment.'}

---
*Generated by VoiceNoteAPI Test Runner*
"""
        
        return md

def main():
    """Main entry point."""
    runner = TestRunner()
    runner.run_all_tests()
    all_passed = runner.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
