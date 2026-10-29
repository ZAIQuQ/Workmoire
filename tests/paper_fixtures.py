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

READING_ABSTRACT = 'We present a mixture of temporal experts for time series forecasting. A routing network selects experts from the current sequence state, while an adaptive training weight balances short and long temporal patterns. Shared representations connect the expert outputs to the forecast head.'
READING_TRANSLATION = '我们提出一种用于时间序列预测的时序专家混合方法。路由网络根据当前序列状态选择专家，自适应训练权重平衡短期与长期时序模式。共享表示将专家输出连接到预测头。'
READING_BRIEF = '## 一句话看懂\n\n通过按状态选择时序专家，将不同时间尺度的模式组合用于预测。\n\n## 核心洞见\n\n- 序列的短期变化与长期结构需要不同的表示，路由网络按当前状态选择适合的专家。\n\n## 技术要点\n\n- 时序编码器生成共享状态表示。\n- 路由网络选择专家并融合其输出。\n- 自适应训练权重平衡不同时间尺度，预测头生成结果。'

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
            fields={'primary':'机器学习','secondary':'时间序列预测','evidence':'We study machine learning methods for time series forecasting and compare prediction errors.'})
    return json.dumps(result,ensure_ascii=False)
