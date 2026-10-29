# -*- coding: utf-8 -*-
"""Plotly figure builders for model-validation dashboards."""
import plotly.graph_objects as go

from ui import theme


def validation_figures(validation, task):
    """Build calibration and per-training-item LOO comparison figures."""
    calibration = go.Figure()
    for segment, part in validation.groupby('分段', sort=True):
        segment_name = str(segment)
        calibration.add_scatter(
            x=part['實測值'], y=part['LOO預測值'], mode='markers',
            name=segment_name, marker=dict(size=8, opacity=.82),
            hovertemplate=('分段: ' + segment_name + '<br>實測: %{x:.2f} MPa'
                           '<br>LOO預測: %{y:.2f} MPa<extra></extra>'))
    low = min(validation['實測值'].min(), validation['LOO預測值'].min())
    high = max(validation['實測值'].max(), validation['LOO預測值'].max())
    margin = max((high - low) * .05, .5)
    calibration.add_scatter(
        x=[low - margin, high + margin], y=[low - margin, high + margin],
        mode='lines', name='理想校準線',
        line=dict(color=theme.COLORS['slate'], dash='dash'))
    calibration.update_layout(
        title=f'{task}：實測值與 LOO 預測校準驗證',
        xaxis_title='實測強度 (MPa)', yaxis_title='LOO 預測強度 (MPa)')
    calibration.update_xaxes(range=[low - margin, high + margin])
    calibration.update_yaxes(range=[low - margin, high + margin],
                             scaleanchor='x', scaleratio=1)

    comparison = go.Figure()
    hover_fields = validation[['型別', '分段']]
    comparison.add_scatter(
        x=validation['訓練資料項目'], y=validation['實測值'],
        mode='lines+markers', name='實測值',
        line=dict(color=theme.COLORS['red'], width=2.5), marker=dict(size=7),
        customdata=hover_fields,
        hovertemplate=('項目: %{x}<br>型別: %{customdata[0]}'
                       '<br>分段: %{customdata[1]}<br>實測: %{y:.2f} MPa'
                       '<extra></extra>'))
    comparison.add_scatter(
        x=validation['訓練資料項目'], y=validation['LOO預測值'],
        mode='lines+markers', name='LOO 預測值',
        line=dict(color=theme.COLORS['blue'], width=2.5),
        marker=dict(size=7, symbol='diamond'), customdata=hover_fields,
        hovertemplate=('項目: %{x}<br>型別: %{customdata[0]}'
                       '<br>分段: %{customdata[1]}<br>LOO預測: %{y:.2f} MPa'
                       '<extra></extra>'))
    comparison.update_layout(
        title=f'{task}：各訓練資料項目的實測與 LOO 預測強度',
        xaxis_title='作為 ground truth 的訓練資料項目',
        yaxis_title='強度 (MPa)', hovermode='x unified')
    comparison.update_xaxes(
        tickangle=-45, categoryorder='array',
        categoryarray=validation['訓練資料項目'].tolist())
    # y 軸預設顯示範圍：30–60 MPa（品管關心的強度區間）。
    # 僅為初始視窗，仍可手動縮放／平移查看範圍外資料。
    comparison.update_yaxes(range=[30, 60])
    return calibration, comparison
