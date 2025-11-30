# Examples

## Table of Contents

- [Basic Examples](#basic-examples)
- [Advanced Use Cases](#advanced-use-cases)
- [Integration Examples](#integration-examples)
- [Real-World Scenarios](#real-world-scenarios)
- [Performance Examples](#performance-examples)
- [Error Handling Examples](#error-handling-examples)

## Basic Examples

### Example 1: Creating a Research Community

```python
import asyncio
from aiecs.domain import (
    CommunityBuilder, CommunityManager, DecisionEngine,
    CommunicationHub, ResourceManager, CollaborativeWorkflowEngine,
    GovernanceType, CommunityRole, ConsensusAlgorithm, ResourceType
)

async def create_research_community():
    """Create a research community with democratic governance."""
    
    # Initialize components
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    decision_engine = DecisionEngine(community_manager)
    communication_hub = CommunicationHub(community_manager)
    resource_manager = ResourceManager(community_manager)
    workflow_engine = CollaborativeWorkflowEngine(community_manager)
    
    # Create community using builder
    community = (CommunityBuilder(integration)
        .with_name("AI Research Lab")
        .with_description("Collaborative AI research and development community")
        .with_governance(GovernanceType.DEMOCRATIC)
        .with_capacity(20)
        .with_template("research_team", {
            "default_roles": ["researcher", "reviewer", "coordinator"],
            "auto_approve_members": False,
            "voting_threshold": 0.6
        })
        .build())
    
    print(f"Created community: {community.name} (ID: {community.community_id})")
    return community

# Run the example
if __name__ == "__main__":
    asyncio.run(create_research_community())
```

### Example 2: Adding Members and Managing Roles

```python
async def manage_community_members():
    """Demonstrate member management operations."""
    
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    
    # Create a community
    community = await community_manager.create_community(
        name="Development Team",
        description="Software development collaboration",
        governance_type=GovernanceType.HIERARCHICAL,
        creator_agent_id="admin_agent",
        capacity=10
    )
    
    # Add members with different roles
    members = [
        ("lead_dev", CommunityRole.ADMIN, {"expertise": "full-stack", "experience": "5_years"}),
        ("senior_dev", CommunityRole.MODERATOR, {"expertise": "backend", "experience": "3_years"}),
        ("junior_dev", CommunityRole.MEMBER, {"expertise": "frontend", "experience": "1_year"}),
        ("qa_engineer", CommunityRole.MEMBER, {"expertise": "testing", "experience": "2_years"}),
        ("observer", CommunityRole.OBSERVER, {"expertise": "product", "experience": "4_years"})
    ]
    
    for agent_id, role, metadata in members:
        member = await community_manager.add_member(
            community.community_id, agent_id, role, metadata
        )
        print(f"Added {agent_id} as {role.value}")
    
    # Update a member's role
    await community_manager.update_member_role(
        community.community_id, "junior_dev", CommunityRole.MODERATOR
    )
    print("Promoted junior_dev to moderator")
    
    # List all members
    community = await community_manager.get_community(community.community_id)
    for member in community.members:
        print(f"Member: {member.agent_id}, Role: {member.role.value}")

asyncio.run(manage_community_members())
```

### Example 3: Decision Making Process

```python
async def decision_making_example():
    """Demonstrate the complete decision-making process."""
    
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    decision_engine = DecisionEngine(community_manager)
    
    # Create community and add members
    community = await community_manager.create_community(
        name="Product Team",
        description="Product development decisions",
        governance_type=GovernanceType.DEMOCRATIC,
        creator_agent_id="product_manager",
        capacity=8
    )
    
    # Add team members
    team_members = ["product_manager", "designer", "developer1", "developer2", "qa_lead"]
    for member_id in team_members:
        await community_manager.add_member(
            community.community_id, member_id, CommunityRole.MEMBER
        )
    
    # Propose a decision
    decision = await decision_engine.propose_decision(
        community_id=community.community_id,
        proposer_id="product_manager",
        title="Choose Next Feature Priority",
        description="Which feature should we prioritize for the next sprint?",
        options=["User Authentication", "Dashboard Redesign", "API Integration", "Mobile App"],
        algorithm=ConsensusAlgorithm.SUPERMAJORITY
    )
    
    print(f"Decision proposed: {decision.title}")
    print(f"Options: {decision.options}")
    
    # Cast votes
    votes = [
        ("product_manager", "User Authentication", 2.0),  # Weighted vote
        ("designer", "Dashboard Redesign", 1.0),
        ("developer1", "API Integration", 1.0),
        ("developer2", "API Integration", 1.0),
        ("qa_lead", "User Authentication", 1.0)
    ]
    
    for voter_id, choice, weight in votes:
        await decision_engine.cast_vote(decision.decision_id, voter_id, choice, weight)
        print(f"{voter_id} voted for {choice} (weight: {weight})")
    
    # Evaluate the decision
    passed, details = await decision_engine.evaluate_decision(
        decision.decision_id, community.community_id, ConsensusAlgorithm.SUPERMAJORITY
    )
    
    print(f"\nDecision Result:")
    print(f"Passed: {passed}")
    print(f"Details: {details}")
    
    if passed:
        winning_option = details.get('winning_option')
        print(f"Winning option: {winning_option}")

asyncio.run(decision_making_example())
```

## Advanced Use Cases

### Example 4: Resource Sharing and Collaboration

```python
async def resource_sharing_example():
    """Demonstrate resource sharing and collaborative work."""
    
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    resource_manager = ResourceManager(community_manager)
    communication_hub = CommunicationHub(community_manager)
    
    # Create a data science community
    community = await community_manager.create_community(
        name="Data Science Team",
        description="Collaborative data science and ML research",
        governance_type=GovernanceType.DEMOCRATIC,
        creator_agent_id="data_lead",
        capacity=12
    )
    
    # Add team members
    team_members = ["data_lead", "ml_engineer", "data_analyst", "researcher"]
    for member_id in team_members:
        await community_manager.add_member(
            community.community_id, member_id, CommunityRole.MEMBER
        )
    
    # Create and share a dataset
    dataset_resource = await resource_manager.create_resource(
        community_id=community.community_id,
        creator_id="data_lead",
        name="Customer Behavior Dataset",
        resource_type=ResourceType.DATA,
        data={
            "file_path": "/data/customer_behavior_2024.parquet",
            "size": "1.2GB",
            "records": 100000,
            "features": 45,
            "schema": {
                "user_id": "string",
                "timestamp": "datetime",
                "action": "string",
                "value": "float"
            }
        },
        metadata={
            "description": "Customer interaction data for Q1 2024",
            "version": "1.0",
            "privacy_level": "internal",
            "retention_days": 365
        }
    )
    
    print(f"Created dataset resource: {dataset_resource.name}")
    
    # Share with specific team members
    await resource_manager.share_resource(
        resource_id=dataset_resource.resource_id,
        from_agent_id="data_lead",
        to_agent_ids=["ml_engineer", "data_analyst"],
        permissions={
            "read": True,
            "write": False,
            "share": False,
            "download": True
        }
    )
    
    # Create a trained model resource
    model_resource = await resource_manager.create_resource(
        community_id=community.community_id,
        creator_id="ml_engineer",
        name="Customer Churn Prediction Model",
        resource_type=ResourceType.MODEL,
        data={
            "model_path": "/models/churn_prediction_v2.pkl",
            "algorithm": "Random Forest",
            "accuracy": 0.89,
            "precision": 0.87,
            "recall": 0.91,
            "training_data": "customer_behavior_2024",
            "features_used": ["action_frequency", "session_duration", "page_views"]
        },
        metadata={
            "framework": "scikit-learn",
            "python_version": "3.9",
            "dependencies": ["pandas", "numpy", "scikit-learn"],
            "model_version": "2.0"
        }
    )
    
    # Share model with all team members
    all_members = [member.agent_id for member in community.members]
    await resource_manager.share_resource(
        resource_id=model_resource.resource_id,
        from_agent_id="ml_engineer",
        to_agent_ids=all_members,
        permissions={
            "read": True,
            "inference": True,
            "evaluate": True,
            "retrain": False
        }
    )
    
    print(f"Shared model with {len(all_members)} team members")
    
    # Send notification about new resources
    await communication_hub.broadcast_message(
        sender_id="data_lead",
        community_id=community.community_id,
        content="New dataset and model resources are now available for the team!",
        message_type=MessageType.NOTIFICATION
    )

asyncio.run(resource_sharing_example())
```

### Example 5: Collaborative Workflow Execution

```python
async def collaborative_workflow_example():
    """Demonstrate multi-agent collaborative workflow execution."""
    
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    workflow_engine = CollaborativeWorkflowEngine(community_manager)
    communication_hub = CommunicationHub(community_manager)
    
    # Create a research community
    community = await community_manager.create_community(
        name="Research Collaboration",
        description="Multi-agent research workflow",
        governance_type=GovernanceType.CONSENSUS,
        creator_agent_id="research_coordinator",
        capacity=6
    )
    
    # Add research team members
    researchers = ["research_coordinator", "data_scientist", "ml_engineer", "domain_expert"]
    for researcher_id in researchers:
        await community_manager.add_member(
            community.community_id, researcher_id, CommunityRole.MEMBER
        )
    
    # Start a collaborative research session
    session = await workflow_engine.start_collaboration_session(
        community_id=community.community_id,
        session_name="Market Analysis Research",
        participants=researchers,
        workflow_config={
            "workflow_type": "research_analysis",
            "steps": [
                {
                    "name": "data_collection",
                    "executor": "data_scientist",
                    "timeout_minutes": 30,
                    "dependencies": []
                },
                {
                    "name": "data_preprocessing",
                    "executor": "data_scientist",
                    "timeout_minutes": 20,
                    "dependencies": ["data_collection"]
                },
                {
                    "name": "model_training",
                    "executor": "ml_engineer",
                    "timeout_minutes": 45,
                    "dependencies": ["data_preprocessing"]
                },
                {
                    "name": "domain_analysis",
                    "executor": "domain_expert",
                    "timeout_minutes": 25,
                    "dependencies": ["model_training"]
                },
                {
                    "name": "report_generation",
                    "executor": "research_coordinator",
                    "timeout_minutes": 15,
                    "dependencies": ["domain_analysis"]
                }
            ],
            "parallel_execution": True,
            "checkpoint_frequency": 5
        }
    )
    
    print(f"Started collaboration session: {session.session_name}")
    
    # Execute workflow steps
    try:
        # Step 1: Data Collection
        data_result = await workflow_engine.execute_workflow_step(
            session_id=session.session_id,
            step_name="data_collection",
            executor_id="data_scientist",
            input_data={
                "data_sources": ["market_data_2024", "competitor_analysis"],
                "collection_method": "api_and_web_scraping"
            }
        )
        print(f"Data collection completed: {data_result['records_collected']} records")
        
        # Step 2: Data Preprocessing
        processed_data = await workflow_engine.execute_workflow_step(
            session_id=session.session_id,
            step_name="data_preprocessing",
            executor_id="data_scientist",
            input_data={
                "raw_data": data_result,
                "cleaning_rules": ["remove_duplicates", "handle_missing_values"],
                "feature_engineering": ["normalization", "encoding"]
            }
        )
        print(f"Data preprocessing completed: {processed_data['features_created']} features")
        
        # Step 3: Model Training (can run in parallel with domain analysis)
        model_task = asyncio.create_task(
            workflow_engine.execute_workflow_step(
                session_id=session.session_id,
                step_name="model_training",
                executor_id="ml_engineer",
                input_data={
                    "processed_data": processed_data,
                    "algorithms": ["random_forest", "gradient_boosting"],
                    "validation_strategy": "cross_validation"
                }
            )
        )
        
        # Step 4: Domain Analysis (parallel execution)
        domain_task = asyncio.create_task(
            workflow_engine.execute_workflow_step(
                session_id=session.session_id,
                step_name="domain_analysis",
                executor_id="domain_expert",
                input_data={
                    "market_context": "technology_sector",
                    "analysis_framework": "swot_analysis",
                    "stakeholders": ["customers", "competitors", "regulators"]
                }
            )
        )
        
        # Wait for parallel tasks to complete
        model_result, domain_result = await asyncio.gather(model_task, domain_task)
        
        print(f"Model training completed: {model_result['best_algorithm']} (accuracy: {model_result['accuracy']})")
        print(f"Domain analysis completed: {domain_result['key_insights']} insights")
        
        # Step 5: Report Generation
        final_report = await workflow_engine.execute_workflow_step(
            session_id=session.session_id,
            step_name="report_generation",
            executor_id="research_coordinator",
            input_data={
                "model_results": model_result,
                "domain_insights": domain_result,
                "report_format": "executive_summary",
                "include_visualizations": True
            }
        )
        
        print(f"Research report generated: {final_report['report_path']}")
        
        # Notify team of completion
        await communication_hub.broadcast_message(
            sender_id="research_coordinator",
            community_id=community.community_id,
            content=f"Research session '{session.session_name}' completed successfully!",
            message_type=MessageType.NOTIFICATION
        )
        
    except Exception as e:
        print(f"Workflow execution failed: {e}")
        # Handle workflow failure and cleanup

asyncio.run(collaborative_workflow_example())
```

## Integration Examples

### Example 6: Custom Agent Adapter

```python
class CustomResearchAgent(AgentAdapter):
    """Custom agent adapter for research-specific tasks."""
    
    def __init__(self, agent_id: str, specialization: str, llm_client=None):
        self.agent_id = agent_id
        self.specialization = specialization
        self.llm_client = llm_client
        self.research_tools = ["data_analysis", "literature_review", "experiment_design"]
    
    async def process_message(self, message: Message) -> Any:
        """Process incoming messages based on type and content."""
        if message.message_type == MessageType.REQUEST:
            return await self.handle_research_request(message.content)
        elif message.message_type == MessageType.SHARE:
            return await self.handle_resource_share(message.content)
        else:
            return await self.handle_general_message(message.content)
    
    async def get_capabilities(self) -> List[AgentCapability]:
        """Return agent capabilities."""
        return [
            AgentCapability(
                name="data_analysis",
                description="Statistical analysis and data visualization",
                parameters={
                    "methods": ["descriptive", "inferential", "predictive"],
                    "tools": ["pandas", "numpy", "matplotlib", "seaborn"]
                }
            ),
            AgentCapability(
                name="literature_review",
                description="Academic literature analysis and synthesis",
                parameters={
                    "sources": ["academic_papers", "conference_proceedings", "journals"],
                    "languages": ["english", "chinese", "spanish"]
                }
            ),
            AgentCapability(
                name="experiment_design",
                description="Design and analyze research experiments",
                parameters={
                    "types": ["controlled", "observational", "quasi_experimental"],
                    "statistical_tests": ["t_test", "anova", "chi_square"]
                }
            )
        ]
    
    async def handle_research_request(self, content: Any) -> Any:
        """Handle research-specific requests."""
        request_type = content.get("type")
        
        if request_type == "data_analysis":
            return await self.perform_data_analysis(content.get("data"))
        elif request_type == "literature_review":
            return await self.perform_literature_review(content.get("topic"))
        elif request_type == "experiment_design":
            return await self.design_experiment(content.get("hypothesis"))
        else:
            return {"error": f"Unknown request type: {request_type}"}
    
    async def perform_data_analysis(self, data: Any) -> Dict[str, Any]:
        """Perform data analysis using specialized tools."""
        # Simulate data analysis
        analysis_result = {
            "summary_statistics": {
                "mean": 42.5,
                "std": 12.3,
                "min": 15.2,
                "max": 89.7
            },
            "correlations": {
                "feature_a_feature_b": 0.73,
                "feature_a_feature_c": -0.45
            },
            "insights": [
                "Strong positive correlation between feature A and B",
                "Negative correlation suggests inverse relationship"
            ]
        }
        return analysis_result
    
    async def perform_literature_review(self, topic: str) -> Dict[str, Any]:
        """Perform literature review on given topic."""
        # Simulate literature review
        review_result = {
            "topic": topic,
            "papers_found": 45,
            "key_papers": [
                {"title": "Recent Advances in AI", "authors": "Smith et al.", "year": 2023},
                {"title": "Machine Learning Applications", "authors": "Johnson et al.", "year": 2023}
            ],
            "research_gaps": [
                "Limited research on real-time applications",
                "Need for more diverse datasets"
            ],
            "recommendations": [
                "Focus on practical implementations",
                "Consider ethical implications"
            ]
        }
        return review_result
    
    async def design_experiment(self, hypothesis: str) -> Dict[str, Any]:
        """Design an experiment to test the hypothesis."""
        # Simulate experiment design
        experiment_design = {
            "hypothesis": hypothesis,
            "experiment_type": "controlled_experiment",
            "variables": {
                "independent": ["treatment_group", "control_group"],
                "dependent": ["performance_metric", "user_satisfaction"]
            },
            "sample_size": 100,
            "duration_weeks": 4,
            "statistical_tests": ["t_test", "chi_square"],
            "expected_outcomes": [
                "Significant difference between groups",
                "Effect size > 0.5"
            ]
        }
        return experiment_design

# Usage example
async def custom_agent_example():
    """Demonstrate custom agent adapter usage."""
    
    # Create custom research agent
    research_agent = CustomResearchAgent(
        agent_id="research_agent_001",
        specialization="machine_learning",
        llm_client=None  # Would be actual LLM client
    )
    
    # Register with adapter registry
    registry = AgentAdapterRegistry()
    registry.register_adapter("research_agent_001", research_agent)
    
    # Get agent capabilities
    capabilities = await research_agent.get_capabilities()
    print("Agent capabilities:")
    for cap in capabilities:
        print(f"- {cap.name}: {cap.description}")
    
    # Test message processing
    test_message = Message(
        sender_id="coordinator",
        recipient_ids=["research_agent_001"],
        message_type=MessageType.REQUEST,
        content={
            "type": "data_analysis",
            "data": {"dataset": "customer_behavior", "size": 10000}
        }
    )
    
    result = await research_agent.process_message(test_message)
    print(f"Analysis result: {result}")

asyncio.run(custom_agent_example())
```

## Real-World Scenarios

### Example 7: Academic Research Collaboration

```python
async def academic_research_scenario():
    """Simulate an academic research collaboration scenario."""
    
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    decision_engine = DecisionEngine(community_manager)
    resource_manager = ResourceManager(community_manager)
    workflow_engine = CollaborativeWorkflowEngine(community_manager)
    
    # Create research lab community
    research_lab = await community_manager.create_community(
        name="AI Ethics Research Lab",
        description="Interdisciplinary research on AI ethics and fairness",
        governance_type=GovernanceType.DEMOCRATIC,
        creator_agent_id="lab_director",
        capacity=15
    )
    
    # Add interdisciplinary team members
    team_members = [
        ("lab_director", CommunityRole.ADMIN, {"field": "computer_science", "expertise": "AI_ethics"}),
        ("ethics_professor", CommunityRole.MODERATOR, {"field": "philosophy", "expertise": "moral_philosophy"}),
        ("law_professor", CommunityRole.MODERATOR, {"field": "law", "expertise": "technology_law"}),
        ("psychologist", CommunityRole.MEMBER, {"field": "psychology", "expertise": "human_behavior"}),
        ("data_scientist", CommunityRole.MEMBER, {"field": "data_science", "expertise": "ML_fairness"}),
        ("sociologist", CommunityRole.MEMBER, {"field": "sociology", "expertise": "social_impact"}),
        ("graduate_student1", CommunityRole.MEMBER, {"field": "computer_science", "expertise": "NLP"}),
        ("graduate_student2", CommunityRole.MEMBER, {"field": "philosophy", "expertise": "ethics"}),
    ]
    
    for member_id, role, metadata in team_members:
        await community_manager.add_member(
            research_lab.community_id, member_id, role, metadata
        )
    
    # Propose research direction decision
    research_decision = await decision_engine.propose_decision(
        community_id=research_lab.community_id,
        proposer_id="lab_director",
        title="Choose Primary Research Focus for Next Year",
        description="Which area of AI ethics should be our primary research focus?",
        options=[
            "Algorithmic Bias in Hiring Systems",
            "Privacy in AI-Powered Healthcare",
            "Autonomous Vehicle Decision Making",
            "AI in Criminal Justice Systems"
        ],
        algorithm=ConsensusAlgorithm.WEIGHTED_VOTING
    )
    
    # Cast weighted votes based on expertise
    votes = [
        ("lab_director", "Algorithmic Bias in Hiring Systems", 2.0),
        ("ethics_professor", "AI in Criminal Justice Systems", 2.0),
        ("law_professor", "Privacy in AI-Powered Healthcare", 2.0),
        ("psychologist", "Algorithmic Bias in Hiring Systems", 1.5),
        ("data_scientist", "Algorithmic Bias in Hiring Systems", 2.0),
        ("sociologist", "AI in Criminal Justice Systems", 1.5),
        ("graduate_student1", "Autonomous Vehicle Decision Making", 1.0),
        ("graduate_student2", "AI in Criminal Justice Systems", 1.0),
    ]
    
    for voter_id, choice, weight in votes:
        await decision_engine.cast_vote(research_decision.decision_id, voter_id, choice, weight)
    
    # Evaluate decision
    passed, details = await decision_engine.evaluate_decision(
        research_decision.decision_id, research_lab.community_id
    )
    
    winning_topic = details.get('winning_option')
    print(f"Research focus chosen: {winning_topic}")
    
    # Create shared research resources
    literature_review = await resource_manager.create_resource(
        community_id=research_lab.community_id,
        creator_id="ethics_professor",
        name="AI Ethics Literature Review 2024",
        resource_type=ResourceType.KNOWLEDGE,
        data={
            "papers_reviewed": 150,
            "key_themes": ["fairness", "transparency", "accountability", "privacy"],
            "research_gaps": ["cross-cultural studies", "long-term impact assessment"],
            "bibliography": "ai_ethics_bibliography_2024.bib"
        },
        metadata={
            "review_period": "2024",
            "languages": ["english", "chinese", "spanish"],
            "update_frequency": "quarterly"
        }
    )
    
    # Start collaborative research session
    research_session = await workflow_engine.start_collaboration_session(
        community_id=research_lab.community_id,
        session_name=f"Research on {winning_topic}",
        participants=[member[0] for member in team_members],
        workflow_config={
            "workflow_type": "academic_research",
            "phases": [
                "literature_review",
                "hypothesis_development",
                "experimental_design",
                "data_collection",
                "analysis",
                "paper_writing"
            ],
            "timeline_months": 12,
            "milestones": [
                "Literature review complete",
                "Research proposal approved",
                "Data collection finished",
                "Analysis complete",
                "Paper submitted"
            ]
        }
    )
    
    print(f"Research session started: {research_session.session_name}")
    return research_lab, research_session

asyncio.run(academic_research_scenario())
```

### Example 8: Corporate Innovation Team

```python
async def corporate_innovation_scenario():
    """Simulate a corporate innovation team scenario."""
    
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    decision_engine = DecisionEngine(community_manager)
    resource_manager = ResourceManager(community_manager)
    workflow_engine = CollaborativeWorkflowEngine(community_manager)
    
    # Create innovation team
    innovation_team = await community_manager.create_community(
        name="Product Innovation Team",
        description="Cross-functional team for product innovation and development",
        governance_type=GovernanceType.HIERARCHICAL,
        creator_agent_id="vp_product",
        capacity=12
    )
    
    # Add cross-functional team members
    team_members = [
        ("vp_product", CommunityRole.ADMIN, {"department": "product", "level": "executive"}),
        ("product_manager", CommunityRole.MODERATOR, {"department": "product", "level": "senior"}),
        ("engineering_lead", CommunityRole.MODERATOR, {"department": "engineering", "level": "senior"}),
        ("design_lead", CommunityRole.MODERATOR, {"department": "design", "level": "senior"}),
        ("marketing_manager", CommunityRole.MEMBER, {"department": "marketing", "level": "senior"}),
        ("sales_representative", CommunityRole.MEMBER, {"department": "sales", "level": "senior"}),
        ("data_analyst", CommunityRole.MEMBER, {"department": "analytics", "level": "mid"}),
        ("ux_researcher", CommunityRole.MEMBER, {"department": "design", "level": "mid"}),
        ("backend_engineer", CommunityRole.MEMBER, {"department": "engineering", "level": "mid"}),
        ("frontend_engineer", CommunityRole.MEMBER, {"department": "engineering", "level": "mid"}),
    ]
    
    for member_id, role, metadata in team_members:
        await community_manager.add_member(
            innovation_team.community_id, member_id, role, metadata
        )
    
    # Propose product feature decision
    feature_decision = await decision_engine.propose_decision(
        community_id=innovation_team.community_id,
        proposer_id="product_manager",
        title="Q2 Product Feature Priority",
        description="Which feature should we prioritize for Q2 development?",
        options=[
            "AI-Powered Recommendations",
            "Real-time Collaboration Tools",
            "Advanced Analytics Dashboard",
            "Mobile App Redesign"
        ],
        algorithm=ConsensusAlgorithm.SUPERMAJORITY
    )
    
    # Cast votes with business context
    votes = [
        ("vp_product", "AI-Powered Recommendations", 3.0),  # Executive weight
        ("product_manager", "Real-time Collaboration Tools", 2.0),
        ("engineering_lead", "Advanced Analytics Dashboard", 2.0),
        ("design_lead", "Mobile App Redesign", 2.0),
        ("marketing_manager", "AI-Powered Recommendations", 1.5),
        ("sales_representative", "Real-time Collaboration Tools", 1.5),
        ("data_analyst", "Advanced Analytics Dashboard", 2.0),
        ("ux_researcher", "Mobile App Redesign", 1.5),
        ("backend_engineer", "AI-Powered Recommendations", 1.0),
        ("frontend_engineer", "Mobile App Redesign", 1.0),
    ]
    
    for voter_id, choice, weight in votes:
        await decision_engine.cast_vote(feature_decision.decision_id, voter_id, choice, weight)
    
    # Evaluate decision
    passed, details = await decision_engine.evaluate_decision(
        feature_decision.decision_id, innovation_team.community_id
    )
    
    chosen_feature = details.get('winning_option')
    print(f"Chosen feature for Q2: {chosen_feature}")
    
    # Create shared product resources
    market_research = await resource_manager.create_resource(
        community_id=innovation_team.community_id,
        creator_id="marketing_manager",
        name="Market Research Q1 2024",
        resource_type=ResourceType.DATA,
        data={
            "survey_responses": 5000,
            "key_insights": [
                "Users want more personalized experiences",
                "Mobile usage increased 40%",
                "Collaboration tools are highly requested"
            ],
            "competitor_analysis": {
                "competitor_a": {"market_share": 0.35, "strengths": ["AI", "UX"]},
                "competitor_b": {"market_share": 0.25, "strengths": ["price", "features"]}
            }
        },
        metadata={
            "research_period": "Q1_2024",
            "methodology": "online_survey",
            "confidence_level": 0.95
        }
    )
    
    # Start product development session
    dev_session = await workflow_engine.start_collaboration_session(
        community_id=innovation_team.community_id,
        session_name=f"Development of {chosen_feature}",
        participants=[member[0] for member in team_members],
        workflow_config={
            "workflow_type": "product_development",
            "sprint_duration_weeks": 2,
            "total_sprints": 6,
            "phases": [
                "requirements_gathering",
                "design_and_prototyping",
                "development",
                "testing",
                "deployment",
                "monitoring"
            ],
            "success_metrics": [
                "user_adoption_rate",
                "performance_improvement",
                "customer_satisfaction"
            ]
        }
    )
    
    print(f"Product development session started: {dev_session.session_name}")
    return innovation_team, dev_session

asyncio.run(corporate_innovation_scenario())
```

## Performance Examples

### Example 9: High-Performance Community Operations

```python
async def performance_optimization_example():
    """Demonstrate performance optimization techniques."""
    
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    decision_engine = DecisionEngine(community_manager)
    resource_manager = ResourceManager(community_manager)
    
    # Create a large community
    large_community = await community_manager.create_community(
        name="Large Scale Research Community",
        description="High-performance community for large-scale research",
        governance_type=GovernanceType.DEMOCRATIC,
        creator_agent_id="admin",
        capacity=100
    )
    
    # Batch add members for performance
    member_batch = []
    for i in range(50):  # Add 50 members
        member_batch.append({
            "agent_id": f"researcher_{i:03d}",
            "role": CommunityRole.MEMBER,
            "metadata": {"specialization": f"field_{i % 10}"}
        })
    
    # Add members in parallel
    add_tasks = [
        community_manager.add_member(
            large_community.community_id,
            member["agent_id"],
            member["role"],
            member["metadata"]
        )
        for member in member_batch
    ]
    
    start_time = asyncio.get_event_loop().time()
    await asyncio.gather(*add_tasks)
    end_time = asyncio.get_event_loop().time()
    
    print(f"Added {len(member_batch)} members in {end_time - start_time:.2f} seconds")
    
    # Batch create resources
    resource_batch = []
    for i in range(20):  # Create 20 resources
        resource_batch.append({
            "name": f"Dataset_{i:03d}",
            "resource_type": ResourceType.DATA,
            "data": {"size": f"{i * 100}MB", "records": i * 1000},
            "creator_id": f"researcher_{i % 10:03d}"
        })
    
    # Create resources in parallel
    create_tasks = [
        resource_manager.create_resource(
            community_id=large_community.community_id,
            creator_id=resource["creator_id"],
            name=resource["name"],
            resource_type=resource["resource_type"],
            data=resource["data"]
        )
        for resource in resource_batch
    ]
    
    start_time = asyncio.get_event_loop().time()
    resources = await asyncio.gather(*create_tasks)
    end_time = asyncio.get_event_loop().time()
    
    print(f"Created {len(resources)} resources in {end_time - start_time:.2f} seconds")
    
    # Batch decision voting
    decision = await decision_engine.propose_decision(
        community_id=large_community.community_id,
        proposer_id="admin",
        title="Research Direction Vote",
        description="Choose the primary research direction",
        options=["AI", "ML", "Data Science", "Robotics"],
        algorithm=ConsensusAlgorithm.SIMPLE_MAJORITY
    )
    
    # Cast votes in parallel
    vote_tasks = []
    for i in range(50):
        choice = ["AI", "ML", "Data Science", "Robotics"][i % 4]
        vote_tasks.append(
            decision_engine.cast_vote(
                decision.decision_id,
                f"researcher_{i:03d}",
                choice
            )
        )
    
    start_time = asyncio.get_event_loop().time()
    await asyncio.gather(*vote_tasks)
    end_time = asyncio.get_event_loop().time()
    
    print(f"Cast {len(vote_tasks)} votes in {end_time - start_time:.2f} seconds")
    
    # Evaluate decision
    passed, details = await decision_engine.evaluate_decision(
        decision.decision_id, large_community.community_id
    )
    
    print(f"Decision result: {details.get('winning_option')} (passed: {passed})")

asyncio.run(performance_optimization_example())
```

## Error Handling Examples

### Example 10: Comprehensive Error Handling

```python
async def error_handling_example():
    """Demonstrate comprehensive error handling patterns."""
    
    integration = CommunityIntegration()
    community_manager = CommunityManager(integration)
    decision_engine = DecisionEngine(community_manager)
    resource_manager = ResourceManager(community_manager)
    
    # Create a test community
    community = await community_manager.create_community(
        name="Error Handling Test Community",
        description="Community for testing error scenarios",
        governance_type=GovernanceType.DEMOCRATIC,
        creator_agent_id="test_admin",
        capacity=5
    )
    
    # Test 1: Community not found error
    try:
        await community_manager.get_community("nonexistent_community")
    except CommunityNotFoundError as e:
        print(f"Caught expected error: {e}")
    
    # Test 2: Member already exists error
    await community_manager.add_member(
        community.community_id, "test_member", CommunityRole.MEMBER
    )
    
    try:
        await community_manager.add_member(
            community.community_id, "test_member", CommunityRole.MEMBER
        )
    except MembershipError as e:
        print(f"Caught expected error: {e}")
    
    # Test 3: Community capacity exceeded
    try:
        # Add more members than capacity allows
        for i in range(10):
            await community_manager.add_member(
                community.community_id, f"member_{i}", CommunityRole.MEMBER
            )
    except CommunityCapacityError as e:
        print(f"Caught expected error: {e}")
    
    # Test 4: Resource access denied
    resource = await resource_manager.create_resource(
        community_id=community.community_id,
        creator_id="test_admin",
        name="Private Resource",
        resource_type=ResourceType.DATA,
        data={"sensitive": "data"}
    )
    
    try:
        await resource_manager.get_resource(
            resource.resource_id, "unauthorized_agent"
        )
    except AccessDeniedError as e:
        print(f"Caught expected error: {e}")
    
    # Test 5: Decision not found
    try:
        await decision_engine.evaluate_decision(
            "nonexistent_decision", community.community_id
        )
    except DecisionNotFoundError as e:
        print(f"Caught expected error: {e}")
    
    # Test 6: Quorum not met
    decision = await decision_engine.propose_decision(
        community_id=community.community_id,
        proposer_id="test_admin",
        title="Test Decision",
        description="A test decision",
        options=["Yes", "No"],
        algorithm=ConsensusAlgorithm.UNANIMOUS
    )
    
    # Cast only one vote (unanimous requires all)
    await decision_engine.cast_vote(
        decision.decision_id, "test_member", "Yes"
    )
    
    try:
        await decision_engine.evaluate_decision(
            decision.decision_id, community.community_id
        )
    except QuorumNotMetError as e:
        print(f"Caught expected error: {e}")
    
    # Test 7: Graceful error recovery
    async def safe_community_operation():
        """Demonstrate safe error handling with recovery."""
        try:
            # Attempt risky operation
            result = await community_manager.add_member(
                "nonexistent_community", "new_member", CommunityRole.MEMBER
            )
            return result
        except CommunityNotFoundError:
            print("Community not found, creating new one...")
            # Recovery: create the community first
            new_community = await community_manager.create_community(
                name="Recovery Community",
                description="Created during error recovery",
                governance_type=GovernanceType.DEMOCRATIC,
                creator_agent_id="recovery_admin",
                capacity=10
            )
            # Retry the operation
            return await community_manager.add_member(
                new_community.community_id, "new_member", CommunityRole.MEMBER
            )
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    result = await safe_community_operation()
    if result:
        print(f"Operation succeeded: {result.agent_id}")
    
    # Test 8: Retry mechanism with exponential backoff
    async def retry_with_backoff(operation, max_retries=3):
        """Retry operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
    
    # Example usage of retry mechanism
    async def unreliable_operation():
        """Simulate an unreliable operation."""
        import random
        if random.random() < 0.7:  # 70% failure rate
            raise Exception("Simulated failure")
        return "Success!"
    
    try:
        result = await retry_with_backoff(unreliable_operation)
        print(f"Retry succeeded: {result}")
    except Exception as e:
        print(f"All retries failed: {e}")

asyncio.run(error_handling_example())
```

These examples demonstrate the comprehensive capabilities of the DOMAIN_COMMUNITY module, from basic operations to advanced use cases, performance optimization, and robust error handling. Each example is designed to be practical and applicable to real-world scenarios.
