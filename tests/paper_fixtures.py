"""Fictional paper facts for isolated tests; no real author or document data."""
import json

PROFILE_TEXT = '''Synthetic Sequence Study
Example Author One and Example Author Two
Example University
Corresponding author: Example Author Two, Example Learning Lab.
Accepted at Example Conference 2026.
We study machine learning methods for time series forecasting and compare prediction errors.
The experiments use synthetic sequences and report limitations of short training histories.
'''

def analysis_fixture(brief='## 一句话看懂\n\nSynthetic brief.', profile=False):
    result={'brief':brief}
    if profile:
        result.update(
            title={'name':'Synthetic Sequence Study','evidence':'Synthetic Sequence Study'},
            publication={'status':'accepted','venue':'Example Conference','year':'2026','evidence':'Accepted at Example Conference 2026.'},
            authors=[{'name':name,'evidence':'Example Author One and Example Author Two'} for name in ['Example Author One','Example Author Two']],
            affiliations=[{'name':'Example University','evidence':'Example University'}],
            corresponding_authors=[{'name':'Example Author Two','evidence':'Corresponding author: Example Author Two, Example Learning Lab.'}],
            labs=[{'name':'Example Learning Lab','lead':'Example Author Two','evidence':'Corresponding author: Example Author Two, Example Learning Lab.'}],
            fields={'primary':'机器学习','secondary':'时间序列预测','reason':'研究学习方法在时序预测中的应用。','evidence':'We study machine learning methods for time series forecasting and compare prediction errors.'})
    return json.dumps(result,ensure_ascii=False)
