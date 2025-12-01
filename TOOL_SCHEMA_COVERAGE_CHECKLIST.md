# Tool Schema Coverage Checklist - Target: 90%+ Coverage

**Goal**: Achieve 90%+ schema coverage for all 30 registered tools  
**Current Overall Coverage**: 35.5%  
**Target Coverage**: 90%+ per tool

---

## ✅ Already at 90%+ Coverage (7 tools) - Maintenance Only

### Statistics Tools
- [x] `ai_data_analysis_orchestrator` - ✅ 100% (3 methods, 6 schemas) - **MAINTAIN**
- [x] `ai_insight_generator` - ✅ 100% (3 methods, 6 schemas) - **MAINTAIN**
- [x] `ai_report_orchestrator` - ✅ 100% (3 methods, 6 schemas) - **MAINTAIN**
- [x] `data_profiler` - ✅ 100% (3 methods, 6 schemas) - **MAINTAIN**
- [x] `data_transformer` - ✅ 100% (4 methods, 8 schemas) - **MAINTAIN**
- [x] `data_visualizer` - ✅ 100% (3 methods, 6 schemas) - **MAINTAIN**
- [x] `statistical_analyzer` - ✅ 100% (4 methods, 8 schemas) - **MAINTAIN**

**Action**: Monitor for new methods, ensure new methods get schemas immediately

---

## 🔴 CRITICAL PRIORITY - 0% Coverage (11 tools)

### Task Tools - High Impact
- [ ] **`pandas`** - ❌ 0% → 🎯 90%+ (38 methods, 0 schemas)
  - [ ] Add schemas for data reading methods (read_csv, read_json, read_excel) - ~5 methods
  - [ ] Add schemas for filtering/selection methods (filter, select_columns, drop_columns) - ~5 methods
  - [ ] Add schemas for grouping/aggregation methods (groupby, pivot_table, aggregate) - ~5 methods
  - [ ] Add schemas for merging/concatenation methods (merge, concat, join) - ~4 methods
  - [ ] Add schemas for transformation methods (sort_values, rename_columns, replace_values) - ~6 methods
  - [ ] Add schemas for data cleaning methods (fill_na, strip_strings, to_numeric) - ~5 methods
  - [ ] Add schemas for statistical methods (mean, sum, count, min, max) - ~5 methods
  - [ ] Add schemas for window functions (rolling) - ~1 method
  - [ ] Add schemas for sampling/viewing methods (head, tail, sample) - ~2 methods
  - [ ] Verify all 38 methods have schemas and coverage ≥90%

- [ ] **`stats`** - ❌ 0% → 🎯 90%+ (10 methods, 0 schemas)
  - [ ] Add schema for descriptive statistics method
  - [ ] Add schema for correlation analysis method
  - [ ] Add schema for hypothesis testing method
  - [ ] Add schema for regression analysis method
  - [ ] Add schema for distribution analysis method
  - [ ] Add schema for confidence interval calculation method
  - [ ] Add schema for statistical significance testing method
  - [ ] Add schema for data distribution fitting method
  - [ ] Add schema for outlier detection method
  - [ ] Add schema for statistical summary method
  - [ ] Verify all 10 methods have schemas and coverage ≥90%

- [ ] **`research`** - ❌ 0% → 🎯 90%+ (8 methods, 0 schemas)
  - [ ] Add schema for research search method
  - [ ] Add schema for research analysis method
  - [ ] Add schema for research summarization method
  - [ ] Add schema for citation extraction method
  - [ ] Add schema for research filtering method
  - [ ] Add schema for research aggregation method
  - [ ] Add schema for research export method
  - [ ] Add schema for research validation method
  - [ ] Verify all 8 methods have schemas and coverage ≥90%

- [ ] **`report`** - ❌ 0% → 🎯 90%+ (8 methods, 0 schemas)
  - [ ] Add schema for report generation method
  - [ ] Add schema for report formatting method
  - [ ] Add schema for report export method
  - [ ] Add schema for report template method
  - [ ] Add schema for report section method
  - [ ] Add schema for report styling method
  - [ ] Add schema for report validation method
  - [ ] Add schema for report merge method
  - [ ] Verify all 8 methods have schemas and coverage ≥90%

- [ ] **`image`** - ❌ 0% → 🎯 90%+ (6 methods, 1 schema)
  - [ ] Review existing BaseFileSchema and ensure it's properly used
  - [ ] Add schema for image processing method
  - [ ] Add schema for image transformation method
  - [ ] Add schema for image filtering method
  - [ ] Add schema for image enhancement method
  - [ ] Add schema for image analysis method
  - [ ] Add schema for image export method
  - [ ] Verify all 6 methods have schemas and coverage ≥90%

- [ ] **`office`** - ❌ 0% → 🎯 90%+ (7 methods, 1 schema)
  - [ ] Review existing BaseFileSchema and ensure it's properly used
  - [ ] Add schema for document processing method
  - [ ] Add schema for spreadsheet processing method
  - [ ] Add schema for presentation processing method
  - [ ] Add schema for office file conversion method
  - [ ] Add schema for office file extraction method
  - [ ] Add schema for office file manipulation method
  - [ ] Add schema for office file validation method
  - [ ] Verify all 7 methods have schemas and coverage ≥90%

- [ ] **`scraper`** - ❌ 0% → 🎯 90%+ (2 methods, 0 schemas)
  - [ ] Add schema for web scraping method
  - [ ] Add schema for content extraction method
  - [ ] Verify all 2 methods have schemas and coverage ≥90%

### Knowledge Graph Tools - Needs Investigation
- [ ] **`graph_reasoning`** - ❌ 0% → 🎯 90%+ (3 methods, 5 schemas found)
  - [ ] Investigate why schemas exist but aren't matched to methods
  - [ ] Fix schema-method matching (QueryPlanSchema, MultiHopSchema, InferenceSchema, etc.)
  - [ ] Ensure all 3 methods have corresponding schemas
  - [ ] Verify coverage ≥90%

- [ ] **`graph_search`** - ❌ 0% → 🎯 90%+ (0 methods detected, 7 schemas found)
  - [ ] Investigate method detection issue - methods may exist but weren't detected
  - [ ] Review tool implementation to identify actual methods
  - [ ] Match existing schemas (VectorSearchSchema, GraphSearchSchema, HybridSearchSchema, etc.) to methods
  - [ ] Add schemas for any methods without schemas
  - [ ] Verify coverage ≥90%

- [ ] **`kg_builder`** - ❌ 0% → 🎯 90%+ (0 methods detected, 3 schemas found)
  - [ ] Investigate method detection issue
  - [ ] Review tool implementation to identify actual methods
  - [ ] Match existing schemas (BuildFromTextSchema, BuildFromDocumentSchema, GetStatsSchema) to methods
  - [ ] Add schemas for any methods without schemas
  - [ ] Verify coverage ≥90%

### Search Tools
- [ ] **`search`** - ❌ 0% → 🎯 90%+ (0 methods detected, 0 schemas)
  - [ ] Investigate method detection issue - search tool may have methods defined differently
  - [ ] Review tool implementation to identify actual methods
  - [ ] Add schemas for all identified methods
  - [ ] Verify coverage ≥90%

### Task Tools - Special Cases
- [ ] **`classifier`** - ❌ 0% → 🎯 90%+ (0 methods detected, 12 schemas found)
  - [ ] Investigate method detection issue
  - [ ] Review tool implementation to identify actual methods
  - [ ] Match existing schemas to methods
  - [ ] Add schemas for any methods without schemas
  - [ ] Verify coverage ≥90%

---

## 🟡 HIGH PRIORITY - 50-89% Coverage (8 tools)

### Statistics Tools - Near Target
- [ ] **`data_loader`** - ⚠️ 75% → 🎯 90%+ (4 methods, 8 schemas)
  - [ ] Identify the 1 method missing schema (25% = 1/4 methods)
  - [ ] Add schema for missing method
  - [ ] Verify coverage ≥90%

- [ ] **`model_trainer`** - ⚠️ 75% → 🎯 90%+ (4 methods, 6 schemas)
  - [ ] Identify the 1 method missing schema (25% = 1/4 methods)
  - [ ] Add schema for missing method
  - [ ] Verify coverage ≥90%

### Docs Tools - Need Improvement
- [ ] **`document_writer`** - ⚠️ 80% → 🎯 90%+ (5 methods, 10 schemas)
  - [ ] Identify the 1 method missing schema (20% = 1/5 methods)
  - [ ] Add schema for missing method
  - [ ] Verify coverage ≥90%

- [ ] **`apisource`** - ⚠️ 80% → 🎯 90%+ (5 methods, 8 schemas)
  - [ ] Identify the 1 method missing schema (20% = 1/5 methods)
  - [ ] Add schema for missing method
  - [ ] Verify coverage ≥90%

- [ ] **`chart`** - ⚠️ 66.7% → 🎯 90%+ (3 methods, 6 schemas)
  - [ ] Identify the 1 method missing schema (33.3% = 1/3 methods)
  - [ ] Add schema for missing method
  - [ ] Verify coverage ≥90%

- [ ] **`ai_document_writer_orchestrator`** - ⚠️ 58.3% → 🎯 90%+ (12 methods, 20 schemas)
  - [ ] Identify the 5 methods missing schemas (41.7% = 5/12 methods)
  - [ ] Add schemas for missing methods
  - [ ] Verify coverage ≥90%

- [ ] **`document_layout`** - ⚠️ 50% → 🎯 90%+ (8 methods, 10 schemas)
  - [ ] Identify the 4 methods missing schemas (50% = 4/8 methods)
  - [ ] Add schemas for missing methods
  - [ ] Verify coverage ≥90%

- [ ] **`document_parser`** - ⚠️ 50% → 🎯 90%+ (2 methods, 4 schemas)
  - [ ] Identify the 1 method missing schema (50% = 1/2 methods)
  - [ ] Add schema for missing method
  - [ ] Verify coverage ≥90%

---

## 🟢 MEDIUM PRIORITY - 40-49% Coverage (3 tools)

### Docs Tools
- [ ] **`ai_document_orchestrator`** - ❌ 40% → 🎯 90%+ (5 methods, 6 schemas)
  - [ ] Identify the 3 methods missing schemas (60% = 3/5 methods)
  - [ ] Add schemas for missing methods
  - [ ] Verify coverage ≥90%

- [ ] **`content_insertion`** - ❌ 44.4% → 🎯 90%+ (9 methods, 10 schemas)
  - [ ] Identify the 5 methods missing schemas (55.6% = 5/9 methods)
  - [ ] Add schemas for missing methods
  - [ ] Verify coverage ≥90%

- [ ] **`document_creator`** - ❌ 42.9% → 🎯 90%+ (7 methods, 8 schemas)
  - [ ] Identify the 4 methods missing schemas (57.1% = 4/7 methods)
  - [ ] Add schemas for missing methods
  - [ ] Verify coverage ≥90%

---

## 📊 Progress Tracking

### Overall Statistics
- **Total Tools**: 30
- **Tools at 90%+**: 7 (23.3%)
- **Tools Needing Work**: 23 (76.7%)
- **Current Overall Coverage**: 35.5%
- **Target Overall Coverage**: 90%+

### By Category
- **Statistics Tools**: 7/9 at 90%+ (77.8%) - 2 need work
- **Docs Tools**: 1/7 at 90%+ (14.3%) - 6 need work
- **Task Tools**: 0/9 at 90%+ (0%) - 9 need work
- **Knowledge Graph Tools**: 0/3 at 90%+ (0%) - 3 need investigation
- **API Source Tools**: 0/1 at 90%+ (0%) - 1 needs work
- **Search Tools**: 0/1 at 90%+ (0%) - 1 needs investigation

### Priority Breakdown
- **🔴 Critical (0% coverage)**: 11 tools
- **🟡 High (50-89%)**: 8 tools
- **🟢 Medium (40-49%)**: 3 tools
- **✅ Complete (90%+)**: 7 tools
- **❓ Needs Investigation**: 1 tool (classifier)

---

## 🎯 Implementation Strategy

### Phase 1: Critical Tools (Weeks 1-4)
Focus on tools with 0% coverage that have the highest impact:
1. `pandas` (38 methods) - **WEEK 1-2**
2. `stats` (10 methods) - **WEEK 2**
3. `research` (8 methods) - **WEEK 3**
4. `report` (8 methods) - **WEEK 3**
5. `image`, `office`, `scraper` (15 methods total) - **WEEK 4**

### Phase 2: High Priority (Weeks 5-6)
Complete tools near 90%:
1. `data_loader`, `model_trainer` (2 methods total) - **WEEK 5**
2. `document_writer`, `apisource`, `chart` (3 methods total) - **WEEK 5**
3. `ai_document_writer_orchestrator`, `document_layout`, `document_parser` (10 methods total) - **WEEK 6**

### Phase 3: Medium Priority (Week 7)
Complete remaining docs tools:
1. `ai_document_orchestrator`, `content_insertion`, `document_creator` (12 methods total) - **WEEK 7**

### Phase 4: Investigation & Fixes (Week 8)
Fix method detection and schema matching issues:
1. `graph_reasoning`, `graph_search`, `kg_builder` - Fix schema-method matching
2. `search` - Investigate and add schemas
3. `classifier` - Investigate and fix

### Phase 5: Validation & Quality (Week 9)
- Run `aiecs tools validate-schemas` on all tools
- Verify all tools achieve ≥90% coverage
- Ensure schema quality scores ≥80%
- Update documentation

---

## 📝 Schema Development Guidelines

### For Each Tool:
1. **Review existing methods**: List all public methods (exclude `run`, `run_async`, `run_batch`)
2. **Check existing schemas**: Identify which methods already have schemas
3. **Identify gaps**: List methods without schemas
4. **Prioritize**: Focus on most commonly used methods first
5. **Create schemas**: 
   - Use auto-generation from type annotations when possible
   - Create manual schemas for complex methods requiring detailed validation
   - Follow naming convention: `MethodNameSchema`
6. **Add descriptions**: Ensure all schema fields have meaningful descriptions
7. **Validate**: Run `aiecs tools validate-schemas <tool_name>` to verify
8. **Document**: Update tool documentation with schema information

### Schema Quality Checklist:
- [ ] All methods have schemas (manual or auto-generated)
- [ ] Schema fields have meaningful descriptions (not "Parameter {name}")
- [ ] Type annotations are complete for all parameters
- [ ] Required vs optional parameters are correctly marked
- [ ] Complex types are properly handled (DataFrame → Any, etc.)
- [ ] Schema validation works correctly
- [ ] Schema works with LangChain adapter
- [ ] Coverage ≥90% achieved

---

## 🔍 Validation Commands

```bash
# Check coverage for all tools
python3 scan_tool_schemas.py

# Validate specific tool schemas
aiecs tools validate-schemas <tool_name>

# Validate all tool schemas with details
aiecs tools validate-schemas --verbose

# Show schema examples
aiecs tools validate-schemas <tool_name> --show-examples
```

---

## 📈 Success Metrics

- **Coverage Target**: ≥90% for all 30 tools
- **Quality Target**: Average schema quality score ≥80%
- **Timeline**: 9 weeks (2 months)
- **Completion Criteria**: 
  - All tools have ≥90% schema coverage
  - All schemas pass validation
  - Schema quality scores meet targets
  - Documentation updated

---

**Last Updated**: Generated from schema analysis  
**Next Review**: After Phase 1 completion

