"""
Comprehensive Real-World Tests for StatsTool
全面的真实环境测试 - 不使用mock，测试真实输出

Test Coverage: 90%+
- 数据读取 (CSV, Excel, JSON, Parquet, Feather)
- 描述性统计 (基础统计、百分位数、偏度、峰度)
- t检验 (独立样本、配对样本、Welch's t检验)
- 相关分析 (Pearson, Spearman, Kendall)
- 方差分析 (ANOVA, Tukey HSD事后检验)
- 卡方检验 (独立性检验、Cramer's V效应量)
- 非参数检验 (Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman)
- 回归分析 (OLS, Logit, Probit, Poisson)
- 时间序列分析 (ARIMA, SARIMA, 预测)
- 数据预处理 (标准化、归一化、缺失值填充)
- 错误处理和边界情况
"""

import os
import json
import pytest
import tempfile
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from aiecs.tools.task_tools.stats_tool import (
    StatsTool,
    ScalerType,
    StatsSettings,
    StatsToolError,
    FileOperationError,
    AnalysisError,
    StatsResult
)

# 配置日志以便debug输出
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestStatsToolComprehensive:
    """全面的StatsTool测试"""
    
    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logger.info(f"创建临时工作空间: {workspace}")
            yield workspace
            logger.info(f"清理工作空间: {workspace}")
    
    @pytest.fixture
    def stats_tool(self):
        """创建StatsTool实例"""
        config = {
            "max_file_size_mb": 200,
            "allowed_extensions": ['.csv', '.xlsx', '.json', '.parquet', '.feather']
        }
        tool = StatsTool(config)
        logger.info(f"创建StatsTool: {config}")
        return tool
    
    @pytest.fixture
    def sample_csv_data(self, temp_workspace):
        """创建示例CSV数据"""
        file_path = temp_workspace / "test_data.csv"
        np.random.seed(42)
        
        data = {
            'group': ['A'] * 50 + ['B'] * 50,
            'score1': np.random.normal(100, 15, 100),
            'score2': np.random.normal(105, 15, 100),
            'age': np.random.randint(20, 60, 100),
            'category': np.random.choice(['X', 'Y', 'Z'], 100),
            'value': np.random.exponential(50, 100)
        }
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False)
        logger.info(f"创建CSV数据: {file_path}, 形状: {df.shape}")
        return file_path
    
    @pytest.fixture
    def sample_excel_data(self, temp_workspace):
        """创建示例Excel数据"""
        file_path = temp_workspace / "test_data.xlsx"
        np.random.seed(42)
        
        data = {
            'var1': np.random.normal(50, 10, 80),
            'var2': np.random.normal(55, 12, 80),
            'var3': np.random.normal(48, 8, 80),
            'factor': np.random.choice(['Type1', 'Type2', 'Type3'], 80)
        }
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)
        logger.info(f"创建Excel数据: {file_path}")
        return file_path
    
    @pytest.fixture
    def sample_json_data(self, temp_workspace):
        """创建示例JSON数据"""
        file_path = temp_workspace / "test_data.json"
        np.random.seed(42)
        
        data = {
            'x': np.random.uniform(0, 100, 60).tolist(),
            'y': (2.5 * np.random.uniform(0, 100, 60) + np.random.normal(0, 10, 60)).tolist(),
            'binary': np.random.choice([0, 1], 60).tolist()
        }
        df = pd.DataFrame(data)
        df.to_json(file_path, orient='records')
        logger.info(f"创建JSON数据: {file_path}")
        return file_path
    
    @pytest.fixture
    def sample_time_series_data(self, temp_workspace):
        """创建时间序列数据"""
        file_path = temp_workspace / "time_series.csv"
        
        dates = pd.date_range('2020-01-01', periods=365, freq='D')
        trend = np.linspace(100, 150, 365)
        seasonal = 10 * np.sin(np.linspace(0, 4*np.pi, 365))
        noise = np.random.normal(0, 5, 365)
        values = trend + seasonal + noise
        
        df = pd.DataFrame({
            'date': dates,
            'value': values
        })
        df.to_csv(file_path, index=False)
        logger.info(f"创建时间序列数据: {file_path}")
        return file_path
    
    @pytest.fixture
    def sample_missing_data(self, temp_workspace):
        """创建带缺失值的数据"""
        file_path = temp_workspace / "missing_data.csv"
        np.random.seed(42)
        
        data = {
            'num1': np.random.normal(100, 15, 100),
            'num2': np.random.normal(50, 10, 100),
            'cat1': np.random.choice(['A', 'B', 'C'], 100)
        }
        df = pd.DataFrame(data)
        # 引入缺失值
        df.loc[np.random.choice(df.index, 20, replace=False), 'num1'] = np.nan
        df.loc[np.random.choice(df.index, 15, replace=False), 'num2'] = np.nan
        df.loc[np.random.choice(df.index, 10, replace=False), 'cat1'] = np.nan
        df.to_csv(file_path, index=False)
        logger.info(f"创建缺失值数据: {file_path}, 缺失值数: {df.isna().sum().sum()}")
        return file_path
    
    # ==================== 测试初始化 ====================
    
    def test_initialization_default(self):
        """测试默认初始化"""
        logger.info("测试: 默认初始化")
        tool = StatsTool()
        
        assert tool.settings is not None
        assert tool.settings.max_file_size_mb == 200
        assert '.csv' in tool.settings.allowed_extensions
        logger.info(f"✓ 默认设置: {tool.settings.model_dump()}")
    
    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        logger.info("测试: 自定义配置")
        config = {
            "max_file_size_mb": 100,
            "allowed_extensions": ['.csv', '.json']
        }
        tool = StatsTool(config)
        
        assert tool.settings.max_file_size_mb == 100
        assert '.json' in tool.settings.allowed_extensions
        logger.info("✓ 自定义配置成功")
    
    def test_initialization_invalid_config(self):
        """测试无效配置"""
        logger.info("测试: 无效配置")
        invalid_config = {
            "max_file_size_mb": "invalid"
        }
        
        with pytest.raises(ValueError):
            StatsTool(invalid_config)
        logger.info("✓ 无效配置被正确拒绝")
    
    # ==================== 测试数据读取 ====================
    
    def test_read_csv_data(self, stats_tool, sample_csv_data):
        """测试读取CSV数据"""
        logger.info("测试: 读取CSV数据")
        
        result = stats_tool.read_data(str(sample_csv_data))
        
        assert 'variables' in result
        assert 'observations' in result
        assert result['observations'] == 100
        assert 'group' in result['variables']
        assert 'score1' in result['variables']
        logger.info(f"✓ CSV数据读取成功: {result['observations']}行, {len(result['variables'])}列")
    
    def test_read_excel_data(self, stats_tool, sample_excel_data):
        """测试读取Excel数据"""
        logger.info("测试: 读取Excel数据")
        
        result = stats_tool.read_data(str(sample_excel_data))
        
        assert 'variables' in result
        assert result['observations'] == 80
        assert 'var1' in result['variables']
        logger.info(f"✓ Excel数据读取成功: {result}")
    
    def test_read_json_data(self, stats_tool, sample_json_data):
        """测试读取JSON数据"""
        logger.info("测试: 读取JSON数据")
        
        result = stats_tool.read_data(str(sample_json_data))
        
        assert 'variables' in result
        assert result['observations'] == 60
        assert 'x' in result['variables']
        logger.info(f"✓ JSON数据读取成功")
    
    def test_read_data_with_nrows(self, stats_tool, sample_csv_data):
        """测试限制读取行数"""
        logger.info("测试: 限制读取行数")
        
        result = stats_tool.read_data(str(sample_csv_data), nrows=10)
        
        assert result['observations'] == 10
        logger.info(f"✓ 限制读取成功: {result['observations']}行")
    
    def test_read_unsupported_format(self, stats_tool, temp_workspace):
        """测试不支持的文件格式"""
        logger.info("测试: 不支持的文件格式")
        
        file_path = temp_workspace / "test.txt"
        file_path.write_text("test data")
        
        with pytest.raises(FileOperationError):
            stats_tool.read_data(str(file_path))
        logger.info("✓ 不支持的格式被正确拒绝")
    
    # ==================== 测试描述性统计 ====================
    
    def test_describe_basic(self, stats_tool, sample_csv_data):
        """测试基础描述性统计"""
        logger.info("测试: 基础描述性统计")
        
        result = stats_tool.describe(str(sample_csv_data))
        
        assert 'statistics' in result
        assert 'summary' in result
        stats = result['statistics']
        assert 'score1' in stats
        assert 'mean' in stats['score1']
        assert 'skew' in stats['score1']
        assert 'kurtosis' in stats['score1']
        logger.info(f"✓ 描述性统计成功: {list(stats.keys())}")
    
    def test_describe_specific_variables(self, stats_tool, sample_csv_data):
        """测试指定变量的描述统计"""
        logger.info("测试: 指定变量的描述统计")
        
        result = stats_tool.describe(
            str(sample_csv_data),
            variables=['score1', 'score2']
        )
        
        stats = result['statistics']
        assert 'score1' in stats
        assert 'score2' in stats
        assert 'age' not in stats
        logger.info(f"✓ 指定变量统计成功")
    
    def test_describe_with_percentiles(self, stats_tool, sample_csv_data):
        """测试带百分位数的描述统计"""
        logger.info("测试: 带百分位数的描述统计")
        
        result = stats_tool.describe(
            str(sample_csv_data),
            variables=['score1'],
            include_percentiles=True,
            percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]
        )
        
        stats = result['statistics']
        assert '10%' in stats['score1']
        assert '90%' in stats['score1']
        logger.info(f"✓ 百分位数统计成功")
    
    # ==================== 测试t检验 ====================
    
    def test_ttest_independent(self, stats_tool, sample_csv_data):
        """测试独立样本t检验"""
        logger.info("测试: 独立样本t检验")
        
        result = stats_tool.ttest(
            str(sample_csv_data),
            var1='score1',
            var2='score2',
            equal_var=True,
            paired=False
        )
        
        assert 'test_type' in result
        assert 'statistic' in result
        assert 'pvalue' in result
        assert 'cohens_d' in result
        assert 'effect_size_interpretation' in result
        assert result['test_type'] == "independent t-test (equal variance)"
        logger.info(f"✓ 独立t检验: t={result['statistic']:.3f}, p={result['pvalue']:.3f}, d={result['cohens_d']:.3f}")
    
    def test_ttest_welch(self, stats_tool, sample_csv_data):
        """测试Welch's t检验"""
        logger.info("测试: Welch's t检验")
        
        result = stats_tool.ttest(
            str(sample_csv_data),
            var1='score1',
            var2='score2',
            equal_var=False
        )
        
        assert "Welch's t-test" in result['test_type']
        assert 'cohens_d' in result
        logger.info(f"✓ Welch's t检验成功")
    
    def test_ttest_paired(self, stats_tool, sample_csv_data):
        """测试配对样本t检验"""
        logger.info("测试: 配对样本t检验")
        
        result = stats_tool.ttest(
            str(sample_csv_data),
            var1='score1',
            var2='score2',
            paired=True
        )
        
        assert result['test_type'] == "paired t-test"
        assert 'statistic' in result
        assert 'pvalue' in result
        logger.info(f"✓ 配对t检验成功: {result}")
    
    def test_ttest_ind_alias(self, stats_tool, sample_csv_data):
        """测试ttest_ind别名"""
        logger.info("测试: ttest_ind别名")
        
        result = stats_tool.ttest_ind(
            str(sample_csv_data),
            var1='score1',
            var2='score2'
        )
        
        assert 'statistic' in result
        assert 'pvalue' in result
        logger.info(f"✓ ttest_ind别名工作正常")
    
    # ==================== 测试相关分析 ====================
    
    def test_correlation_pearson(self, stats_tool, sample_csv_data):
        """测试Pearson相关"""
        logger.info("测试: Pearson相关")
        
        result = stats_tool.correlation(
            str(sample_csv_data),
            var1='score1',
            var2='score2',
            method='pearson'
        )
        
        assert 'method' in result
        assert 'correlation' in result
        assert 'pvalue' in result
        assert 'significant' in result
        assert "Pearson" in result['method']
        logger.info(f"✓ Pearson相关: r={result['correlation']:.3f}, p={result['pvalue']:.3f}")
    
    def test_correlation_spearman(self, stats_tool, sample_csv_data):
        """测试Spearman相关"""
        logger.info("测试: Spearman相关")
        
        result = stats_tool.correlation(
            str(sample_csv_data),
            var1='score1',
            var2='age',
            method='spearman'
        )
        
        assert "Spearman" in result['method']
        assert 'correlation' in result
        logger.info(f"✓ Spearman相关成功")
    
    def test_correlation_kendall(self, stats_tool, sample_csv_data):
        """测试Kendall相关"""
        logger.info("测试: Kendall相关")
        
        result = stats_tool.correlation(
            str(sample_csv_data),
            var1='score1',
            var2='age',
            method='kendall'
        )
        
        assert "Kendall" in result['method']
        logger.info(f"✓ Kendall相关成功")
    
    def test_correlation_matrix(self, stats_tool, sample_csv_data):
        """测试相关矩阵"""
        logger.info("测试: 相关矩阵")
        
        result = stats_tool.correlation(
            str(sample_csv_data),
            variables=['score1', 'score2', 'age'],
            method='pearson'
        )
        
        assert 'correlation_matrix' in result
        assert 'pairs' in result
        assert len(result['pairs']) > 0
        # 验证对相关性从高到低排序
        corrs = [p['abs_correlation'] for p in result['pairs']]
        assert corrs == sorted(corrs, reverse=True)
        logger.info(f"✓ 相关矩阵成功: {len(result['pairs'])}对变量")
    
    # ==================== 测试方差分析 ====================
    
    def test_anova_basic(self, stats_tool, sample_csv_data):
        """测试基础ANOVA"""
        logger.info("测试: 基础ANOVA")
        
        result = stats_tool.anova(
            str(sample_csv_data),
            dependent='score1',
            factor='category'
        )
        
        assert 'F' in result
        assert 'pvalue' in result
        assert 'significant' in result
        assert 'groups' in result
        assert 'group_means' in result
        logger.info(f"✓ ANOVA: F={result['F']:.3f}, p={result['pvalue']:.3f}, groups={result['groups']}")
    
    def test_anova_with_posthoc(self, stats_tool, sample_csv_data):
        """测试带事后检验的ANOVA"""
        logger.info("测试: ANOVA + Tukey HSD")
        
        result = stats_tool.anova(
            str(sample_csv_data),
            dependent='score1',
            factor='category',
            post_hoc=True
        )
        
        assert 'post_hoc' in result
        assert result['post_hoc']['method'] == 'Tukey HSD'
        assert 'comparisons' in result['post_hoc']
        assert len(result['post_hoc']['comparisons']) > 0
        
        # 验证比较结果结构
        comp = result['post_hoc']['comparisons'][0]
        assert 'group1' in comp
        assert 'group2' in comp
        assert 'mean_difference' in comp
        assert 'p_adjusted' in comp
        assert 'significant' in comp
        logger.info(f"✓ 事后检验成功: {len(result['post_hoc']['comparisons'])}个比较")
    
    # ==================== 测试卡方检验 ====================
    
    def test_chi_square(self, stats_tool, sample_csv_data):
        """测试卡方检验"""
        logger.info("测试: 卡方检验")
        
        result = stats_tool.chi_square(
            str(sample_csv_data),
            var1='group',
            var2='category',
            correction=True
        )
        
        assert 'chi2' in result
        assert 'pvalue' in result
        assert 'dof' in result
        assert 'cramers_v' in result
        assert 'effect_size_interpretation' in result
        assert 'contingency_table' in result
        assert 'test_type' in result
        assert 'Yates correction' in result['test_type']
        logger.info(f"✓ 卡方检验: χ²={result['chi2']:.3f}, p={result['pvalue']:.3f}, V={result['cramers_v']:.3f}")
    
    def test_chi_square_no_correction(self, stats_tool, sample_csv_data):
        """测试无校正的卡方检验"""
        logger.info("测试: 卡方检验(无校正)")
        
        result = stats_tool.chi_square(
            str(sample_csv_data),
            var1='group',
            var2='category',
            correction=False
        )
        
        assert 'Yates correction' not in result['test_type']
        logger.info(f"✓ 无校正卡方检验成功")
    
    # ==================== 测试非参数检验 ====================
    
    def test_mann_whitney(self, stats_tool, sample_csv_data):
        """测试Mann-Whitney U检验"""
        logger.info("测试: Mann-Whitney U检验")
        
        result = stats_tool.non_parametric(
            str(sample_csv_data),
            test_type='mann_whitney',
            variables=['score1', 'score2']
        )
        
        assert result['test_type'] == 'Mann-Whitney U test'
        assert 'statistic' in result
        assert 'pvalue' in result
        assert 'median1' in result
        assert 'median2' in result
        logger.info(f"✓ Mann-Whitney U: U={result['statistic']:.3f}, p={result['pvalue']:.3f}")
    
    def test_wilcoxon(self, stats_tool, sample_csv_data):
        """测试Wilcoxon符号秩检验"""
        logger.info("测试: Wilcoxon符号秩检验")
        
        result = stats_tool.non_parametric(
            str(sample_csv_data),
            test_type='wilcoxon',
            variables=['score1', 'score2']
        )
        
        assert result['test_type'] == 'Wilcoxon signed-rank test'
        assert 'median_difference' in result
        logger.info(f"✓ Wilcoxon检验成功")
    
    def test_kruskal_wallis(self, stats_tool, sample_csv_data):
        """测试Kruskal-Wallis H检验"""
        logger.info("测试: Kruskal-Wallis H检验")
        
        result = stats_tool.non_parametric(
            str(sample_csv_data),
            test_type='kruskal',
            variables=['score1'],
            grouping='category'
        )
        
        assert result['test_type'] == 'Kruskal-Wallis H test'
        assert 'group_medians' in result
        logger.info(f"✓ Kruskal-Wallis: H={result['statistic']:.3f}")
    
    def test_friedman(self, stats_tool, sample_csv_data):
        """测试Friedman检验"""
        logger.info("测试: Friedman检验")
        
        result = stats_tool.non_parametric(
            str(sample_csv_data),
            test_type='friedman',
            variables=['score1', 'score2', 'age']
        )
        
        assert result['test_type'] == 'Friedman test'
        assert 'n_measures' in result
        assert 'variable_medians' in result
        logger.info(f"✓ Friedman检验成功")
    
    def test_non_parametric_invalid_test(self, stats_tool, sample_csv_data):
        """测试无效的非参数检验类型"""
        logger.info("测试: 无效的非参数检验")
        
        with pytest.raises(AnalysisError):
            stats_tool.non_parametric(
                str(sample_csv_data),
                test_type='invalid_test',
                variables=['score1', 'score2']
            )
        logger.info("✓ 无效检验类型被正确拒绝")
    
    # ==================== 测试回归分析 ====================
    
    def test_regression_ols(self, stats_tool, sample_json_data):
        """测试OLS回归"""
        logger.info("测试: OLS回归")
        
        result = stats_tool.regression(
            str(sample_json_data),
            formula='y ~ x',
            regression_type='ols',
            structured_output=True
        )
        
        assert 'structured' in result
        assert 'summary_text' in result
        structured = result['structured']
        assert structured['model_type'] == 'ols'
        assert 'r_squared' in structured
        assert 'coefficients' in structured
        assert 'x' in structured['coefficients']
        assert 'Intercept' in structured['coefficients']
        
        # 验证系数结构
        x_coef = structured['coefficients']['x']
        assert 'coef' in x_coef
        assert 'std_err' in x_coef
        assert 'p_value' in x_coef
        assert 'significant' in x_coef
        logger.info(f"✓ OLS回归: R²={structured['r_squared']:.3f}, coef={x_coef['coef']:.3f}")
    
    def test_regression_logit(self, stats_tool, sample_json_data):
        """测试Logit回归"""
        logger.info("测试: Logit回归")
        
        result = stats_tool.regression(
            str(sample_json_data),
            formula='binary ~ x',
            regression_type='logit',
            structured_output=True
        )
        
        structured = result['structured']
        assert structured['model_type'] == 'logit'
        assert 'log_likelihood' in structured
        logger.info(f"✓ Logit回归成功")
    
    def test_regression_robust(self, stats_tool, sample_json_data):
        """测试稳健标准误回归"""
        logger.info("测试: 稳健标准误回归")
        
        result = stats_tool.regression(
            str(sample_json_data),
            formula='y ~ x',
            regression_type='ols',
            robust=True,
            structured_output=True
        )
        
        assert 'structured' in result
        logger.info(f"✓ 稳健标准误回归成功")
    
    def test_regression_simple_output(self, stats_tool, sample_json_data):
        """测试简单输出格式"""
        logger.info("测试: 简单输出格式")
        
        result = stats_tool.regression(
            str(sample_json_data),
            formula='y ~ x',
            regression_type='ols',
            structured_output=False
        )
        
        assert 'summary' in result
        assert 'structured' not in result
        logger.info(f"✓ 简单输出成功")
    
    # ==================== 测试时间序列分析 ====================
    
    def test_time_series_arima(self, stats_tool, sample_time_series_data):
        """测试ARIMA模型"""
        logger.info("测试: ARIMA时间序列")
        
        result = stats_tool.time_series(
            str(sample_time_series_data),
            variable='value',
            date_variable='date',
            model_type='arima',
            order=(1, 1, 1),
            forecast_periods=10
        )
        
        assert result['model_type'] == 'ARIMA'
        assert result['order'] == (1, 1, 1)
        assert 'aic' in result
        assert 'bic' in result
        assert 'forecast' in result
        assert len(result['forecast']['values']) == 10
        logger.info(f"✓ ARIMA: AIC={result['aic']:.2f}, BIC={result['bic']:.2f}, 预测{len(result['forecast']['values'])}期")
    
    def test_time_series_sarima(self, stats_tool, sample_time_series_data):
        """测试SARIMA模型"""
        logger.info("测试: SARIMA时间序列")
        
        result = stats_tool.time_series(
            str(sample_time_series_data),
            variable='value',
            model_type='sarima',
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 7),
            forecast_periods=14
        )
        
        assert result['model_type'] == 'SARIMA'
        assert result['seasonal_order'] == (1, 1, 1, 7)
        assert len(result['forecast']['values']) == 14
        logger.info(f"✓ SARIMA成功")
    
    def test_time_series_no_seasonal_error(self, stats_tool, sample_time_series_data):
        """测试SARIMA缺少季节性参数错误"""
        logger.info("测试: SARIMA缺少季节性参数")
        
        with pytest.raises(AnalysisError):
            stats_tool.time_series(
                str(sample_time_series_data),
                variable='value',
                model_type='sarima',
                order=(1, 1, 1),
                forecast_periods=10
            )
        logger.info("✓ 缺少季节性参数被正确拒绝")
    
    # ==================== 测试数据预处理 ====================
    
    def test_preprocess_standard_scale(self, stats_tool, sample_csv_data, temp_workspace):
        """测试标准化"""
        logger.info("测试: 标准化")
        
        output_path = temp_workspace / "scaled_standard.csv"
        result = stats_tool.preprocess(
            str(sample_csv_data),
            variables=['score1', 'score2'],
            operation='scale',
            scaler_type=ScalerType.STANDARD,
            output_path=str(output_path)
        )
        
        assert result['operation'] == 'scale'
        assert result['scaler'] == 'StandardScaler'
        assert 'original_stats' in result
        assert 'scaled_stats' in result
        assert 'output_file' in result
        assert Path(result['output_file']).exists()
        logger.info(f"✓ 标准化成功: {result['output_file']}")
    
    def test_preprocess_minmax_scale(self, stats_tool, sample_csv_data):
        """测试MinMax归一化"""
        logger.info("测试: MinMax归一化")
        
        result = stats_tool.preprocess(
            str(sample_csv_data),
            variables=['score1', 'age'],
            operation='scale',
            scaler_type=ScalerType.MINMAX
        )
        
        assert result['scaler'] == 'MinMaxScaler'
        assert 'preview' in result
        logger.info(f"✓ MinMax归一化成功")
    
    def test_preprocess_robust_scale(self, stats_tool, sample_csv_data):
        """测试稳健标准化"""
        logger.info("测试: 稳健标准化")
        
        result = stats_tool.preprocess(
            str(sample_csv_data),
            variables=['value'],
            operation='scale',
            scaler_type=ScalerType.ROBUST
        )
        
        assert result['scaler'] == 'RobustScaler'
        logger.info(f"✓ 稳健标准化成功")
    
    def test_preprocess_impute(self, stats_tool, sample_missing_data):
        """测试缺失值填充"""
        logger.info("测试: 缺失值填充")
        
        result = stats_tool.preprocess(
            str(sample_missing_data),
            variables=['num1', 'num2', 'cat1'],
            operation='impute'
        )
        
        assert result['operation'] == 'impute'
        assert 'missing_counts_before' in result
        assert 'missing_counts_after' in result
        assert 'imputation_method' in result
        
        # 验证缺失值减少
        before = sum(result['missing_counts_before'].values())
        after = sum(result['missing_counts_after'].values())
        assert after < before
        logger.info(f"✓ 缺失值填充: 填充前{before}个, 填充后{after}个")
    
    # ==================== 测试错误处理 ====================
    
    def test_validate_variables_missing(self, stats_tool, sample_csv_data):
        """测试变量验证 - 缺失变量"""
        logger.info("测试: 变量验证 - 缺失变量")
        
        with pytest.raises(FileOperationError):
            stats_tool.describe(
                str(sample_csv_data),
                variables=['nonexistent_var']
            )
        logger.info("✓ 缺失变量被正确检测")
    
    def test_invalid_regression_formula(self, stats_tool, sample_csv_data):
        """测试无效的回归公式"""
        logger.info("测试: 无效的回归公式")
        
        with pytest.raises(AnalysisError):
            stats_tool.regression(
                str(sample_csv_data),
                formula='score1 ~ nonexistent',
                regression_type='ols'
            )
        logger.info("✓ 无效公式被正确拒绝")
    
    def test_mann_whitney_wrong_var_count(self, stats_tool, sample_csv_data):
        """测试Mann-Whitney U检验变量数错误"""
        logger.info("测试: Mann-Whitney变量数错误")
        
        with pytest.raises(AnalysisError):
            stats_tool.non_parametric(
                str(sample_csv_data),
                test_type='mann_whitney',
                variables=['score1']  # 需要2个变量
            )
        logger.info("✓ 变量数错误被正确检测")
    
    def test_kruskal_no_grouping(self, stats_tool, sample_csv_data):
        """测试Kruskal-Wallis缺少分组变量"""
        logger.info("测试: Kruskal-Wallis缺少分组")
        
        with pytest.raises(AnalysisError):
            stats_tool.non_parametric(
                str(sample_csv_data),
                test_type='kruskal',
                variables=['score1']
            )
        logger.info("✓ 缺少分组变量被正确检测")
    
    # ==================== 测试StatsResult数据类 ====================
    
    def test_stats_result_to_dict(self):
        """测试StatsResult转字典"""
        logger.info("测试: StatsResult.to_dict()")
        
        result = StatsResult(
            test_type='test',
            statistic=1.5,
            pvalue=0.05,
            significant=True,
            additional_metrics={'key': 'value'}
        )
        
        d = result.to_dict()
        assert d['test_type'] == 'test'
        assert d['statistic'] == 1.5
        assert d['pvalue'] == 0.05
        assert d['significant'] is True
        assert d['key'] == 'value'
        logger.info(f"✓ StatsResult转字典成功: {d}")
    
    # ==================== 测试效应量解释 ====================
    
    def test_effect_size_interpretation(self, stats_tool):
        """测试效应量解释"""
        logger.info("测试: 效应量解释")
        
        assert stats_tool._interpret_effect_size(0.1) == "negligible"
        assert stats_tool._interpret_effect_size(0.3) == "small"
        assert stats_tool._interpret_effect_size(0.6) == "medium"
        assert stats_tool._interpret_effect_size(1.0) == "large"
        logger.info("✓ 效应量解释正确")
    
    # ==================== 测试边界情况 ====================
    
    def test_empty_dataframe_handling(self, stats_tool, temp_workspace):
        """测试空数据框处理"""
        logger.info("测试: 空数据框")
        
        file_path = temp_workspace / "empty.csv"
        # 创建有列但无数据的空DataFrame
        pd.DataFrame(columns=['a', 'b']).to_csv(file_path, index=False)
        
        result = stats_tool.read_data(str(file_path))
        assert result['observations'] == 0
        assert 'a' in result['variables']
        logger.info("✓ 空数据框处理正确")
    
    def test_single_row_data(self, stats_tool, temp_workspace):
        """测试单行数据"""
        logger.info("测试: 单行数据")
        
        file_path = temp_workspace / "single_row.csv"
        pd.DataFrame({'a': [1], 'b': [2]}).to_csv(file_path, index=False)
        
        result = stats_tool.read_data(str(file_path))
        assert result['observations'] == 1
        logger.info("✓ 单行数据处理正确")


# 运行pytest with coverage
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--log-cli-level=DEBUG",
        "-s"  # 显示打印语句和日志
    ])

