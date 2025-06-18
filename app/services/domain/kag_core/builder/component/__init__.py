# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

from app.services.domain.kag_core.builder.component.external_graph.external_graph import (
    DefaultExternalGraphLoader,
)
from app.services.domain.kag_core.builder.component.extractor.naive_rag_extractor import NaiveRagExtractor
from app.services.domain.kag_core.builder.component.extractor.schema_free_extractor import SchemaFreeExtractor
from app.services.domain.kag_core.builder.component.extractor.schema_constraint_extractor import (
    SchemaConstraintExtractor,
)
from app.services.domain.kag_core.builder.component.extractor.table_extractor import TableExtractor
from app.services.domain.kag_core.builder.component.aligner.kag_aligner import KAGAligner
from app.services.domain.kag_core.builder.component.aligner.spg_aligner import SPGAligner
from app.services.domain.kag_core.builder.component.postprocessor.kag_postprocessor import KAGPostProcessor

from app.services.domain.kag_core.builder.component.mapping.spg_type_mapping import SPGTypeMapping
from app.services.domain.kag_core.builder.component.mapping.relation_mapping import RelationMapping
from app.services.domain.kag_core.builder.component.mapping.spo_mapping import SPOMapping
from app.services.domain.kag_core.builder.component.scanner.csv_scanner import CSVScanner, CSVStructuredScanner
from app.services.domain.kag_core.builder.component.scanner.json_scanner import JSONScanner
from app.services.domain.kag_core.builder.component.scanner.yuque_scanner import YuqueScanner
from app.services.domain.kag_core.builder.component.scanner.dataset_scanner import (
    MusiqueCorpusScanner,
    HotpotqaCorpusScanner,
)
from app.services.domain.kag_core.builder.component.scanner.file_scanner import FileScanner
from app.services.domain.kag_core.builder.component.scanner.directory_scanner import DirectoryScanner
from app.services.domain.kag_core.builder.component.scanner.odps_scanner import ODPSScanner
from app.services.domain.kag_core.builder.component.scanner.sls_scanner import SLSScanner, SLSConsumerScanner


from app.services.domain.kag_core.builder.component.reader.pdf_reader import PDFReader
from app.services.domain.kag_core.builder.component.reader.markdown_reader import MarkDownReader
from app.services.domain.kag_core.builder.component.reader.docx_reader import DocxReader
from app.services.domain.kag_core.builder.component.reader.txt_reader import TXTReader
from app.services.domain.kag_core.builder.component.reader.mix_reader import MixReader

from app.services.domain.kag_core.builder.component.reader.dict_reader import DictReader


from app.services.domain.kag_core.builder.component.splitter.length_splitter import LengthSplitter
from app.services.domain.kag_core.builder.component.splitter.pattern_splitter import PatternSplitter
from app.services.domain.kag_core.builder.component.splitter.outline_splitter import OutlineSplitter
from app.services.domain.kag_core.builder.component.splitter.semantic_splitter import SemanticSplitter
from app.services.domain.kag_core.builder.component.vectorizer.batch_vectorizer import BatchVectorizer
from app.services.domain.kag_core.builder.component.writer.kg_writer import KGWriter
from app.services.domain.kag_core.builder.component.writer.memory_graph_writer import MemoryGraphWriter


__all__ = [
    "DefaultExternalGraphLoader",
    "SchemaFreeExtractor",
    "SchemaConstraintExtractor",
    "KAGAligner",
    "SPGAligner",
    "KAGPostProcessor",
    "KGWriter",
    "SPGTypeMapping",
    "RelationMapping",
    "SPOMapping",
    "TXTReader",
    "PDFReader",
    "MarkDownReader",
    "DocxReader",
    "MixReader",
    "DictReader",
    "JSONScanner",
    "HotpotqaCorpusScanner",
    "MusiqueCorpusScanner",
    "FileScanner",
    "DirectoryScanner",
    "YuqueScanner",
    "CSVScanner",
    "CSVStructuredScanner",
    "ODPSScanner",
    "LengthSplitter",
    "PatternSplitter",
    "OutlineSplitter",
    "SemanticSplitter",
    "BatchVectorizer",
    "KGWriter",
    "SLSScanner",
    "SLSConsumerScanner",
    "NaiveRagExtractor",
    "TableExtractor",
    "MemoryGraphWriter",
]
