from graphviz import Digraph

def create_flowchart():
    dot = Digraph(comment='Study Methodology', format='png')
    # Removed ordering='out' to rely on group/weight
    dot.attr(rankdir='TB', splines='true', nodesep='0.6', ranksep='0.6')
    
    # Fonts
    dot.attr('node', fontname='Helvetica', fontsize='12', shape='box', style='filled')
    dot.attr('edge', fontname='Helvetica', fontsize='10')
    dot.attr('graph', fontname='Helvetica-Bold', fontsize='14')

    # Colors
    c_primary = '#e1f5fe'   # Blue
    c_secondary = '#f3e5f5' # Purple
    c_process = '#fff3e0'   # Orange
    c_model = '#e8f5e9'     # Green

    # labeljust='c' CENTERS the phase titles
    cluster_attr = {'style': 'rounded,filled', 'fillcolor': '#fafafa', 'margin': '25', 'labeljust': 'c'}

    # ---------------------------------------------------------
    # Phase 1: Data Acquisition
    with dot.subgraph(name='cluster_0') as c:
        c.attr(label='Phase 1: Data Acquisition', **cluster_attr)
        
        with c.subgraph() as header:
            header.attr(rank='same')
            # Grouping is capable of locking vertical alignment
            # We want MIMIC on Left, SIM on Right
            header.node('MIMIC', 'MIMIC-IV\n(Primary Dataset)\nn=852', fillcolor=c_primary, shape='cylinder', group='main_left')
            header.node('SIM', 'Simulated Cohort\n(Method Validation)\nn=852', fillcolor=c_secondary, shape='cylinder', group='main_right')
            
            # Invisible edge to define left-to-right relation
            header.edge('MIMIC', 'SIM', style='invis', weight='50')

    # ---------------------------------------------------------
    # Phase 2: Missing Data
    with dot.subgraph(name='cluster_1') as c:
        # Phase 2 Label Removed (External)
        c.attr(**cluster_attr)
        
        with c.subgraph() as level2:
            level2.attr(rank='same')
            # Observed Missing Data -> Left Group
            level2.node('MIMIC_Miss', 'Observed Missing Data', fillcolor='#ffffff', group='main_left')
            
            # SimGen -> Right Group
            level2.node('SimGen', 'Missing Mechanisms', shape='diamond', fillcolor='#ffffff', group='main_right')
            
            # Constraint: Left to Right
            level2.edge('MIMIC_Miss', 'SimGen', style='invis', weight='50')
        
        # Children of SimGen don't need group constraint, usually they fan out
        c.node('MCAR', 'MCAR', fillcolor=c_process)
        c.node('MAR', 'MAR', fillcolor=c_process)
        c.node('MNAR', 'MNAR', fillcolor=c_process)
        
        c.edge('SimGen', 'MCAR')
        c.edge('SimGen', 'MAR')
        c.edge('SimGen', 'MNAR')

    # ---------------------------------------------------------
    # Phase 3: Imputation
    with dot.subgraph(name='cluster_2') as c:
        # Phase 3 Label Removed (External)
        c.attr(**cluster_attr)
        # We start centering here. We drop the group constraints or start a new 'center' group?
        # Let's try not grouping ImpStart, or grouping it to the center of the diagram?
        # Actually without group, it floats to average position.
        c.node('ImpStart', 'Imputation Methods', shape='diamond', fillcolor='#ffffff')
        
        with c.subgraph() as imp_methods:
            imp_methods.attr(rank='same')
            imp_methods.node('MICE', 'MICE\n(Statistical)', fillcolor=c_process)
            imp_methods.node('MF', 'missForest\n(Ensemble)', fillcolor=c_process)
            imp_methods.node('GAIN', 'GAIN\n(DL)', fillcolor=c_process)
            imp_methods.node('MIDA', 'MIDA\n(Autoencoder)', fillcolor=c_process)
            
            imp_methods.edge('MICE', 'MF', style='invis')
            imp_methods.edge('MF', 'GAIN', style='invis')
            imp_methods.edge('GAIN', 'MIDA', style='invis')

    # ---------------------------------------------------------
    # Phase 4: Modeling
    with dot.subgraph(name='cluster_3') as c:
        # Phase 4 Label Removed (External)
        c.attr(**cluster_attr)
        c.node('Imputed_Data', 'Complete Imputed Datasets', fillcolor=c_process)
        
        c.node('TrainVal', 'Model Training and Validation\n(Split 90/10, 10-Fold CV, Preprocessing)', fillcolor='#ffffff', shape='box')
        
        c.node('Models', 'Survival Models', shape='diamond', fillcolor='#ffffff')
        
        with c.subgraph() as model_list:
            model_list.attr(rank='same')
            model_list.node('RSF', 'RSF\n(Primary)', fillcolor=c_model)
            model_list.node('XGB', 'XGBoost', fillcolor=c_model)
            model_list.node('DS', 'DeepSurv', fillcolor=c_model)
            model_list.node('CWGB', 'Comp-wise\nBoosting', fillcolor=c_model)

    # ---------------------------------------------------------
    # Phase 5: Evaluation
    with dot.subgraph(name='cluster_4') as c:
        # Phase 5 Label Removed (External)
        c.attr(**cluster_attr)
        c.node('Metrics', 'Evaluation', shape='diamond', fillcolor='#ffffff')
        
        with c.subgraph() as outputs:
            outputs.attr(rank='same')
            outputs.node('Perf', 'Performance Metrics\n- C-index\n- Brier\n- CRPS', fillcolor=c_primary)
            outputs.node('Interpret', 'Interpretability', fillcolor=c_secondary)
            outputs.node('Clinical', 'Clinical Utility', fillcolor=c_secondary)

    dot.node('Conclusion', 'Final Conclusion\n& Recommendation', shape='note', fillcolor='#ffffcc')

    # ---------------------------------------------------------
    # EDGES
    
    # Phase 1 -> Phase 2
    # Ensure verticality by strict group weight
    # MIMIC (group main_left) -> MIMIC_Miss (group main_left)
    dot.edge('MIMIC', 'MIMIC_Miss', label='Assess Missingness', weight='10')
    # SIM (group main_right) -> SimGen (group main_right)
    dot.edge('SIM', 'SimGen', label='Amputation', weight='10')
    
    # Phase 2 -> Phase 3
    # MIMIC_Miss -> ImpStart
    dot.edge('MIMIC_Miss', 'ImpStart')
    # Mechanisms -> ImpStart
    dot.edge('MCAR', 'ImpStart')
    dot.edge('MAR', 'ImpStart')
    dot.edge('MNAR', 'ImpStart')
    
    # Phase 3
    dot.edge('ImpStart', 'MICE')
    dot.edge('ImpStart', 'MF')
    dot.edge('ImpStart', 'GAIN')
    dot.edge('ImpStart', 'MIDA')
    
    dot.edge('MICE', 'Imputed_Data')
    dot.edge('MF', 'Imputed_Data')
    dot.edge('GAIN', 'Imputed_Data')
    dot.edge('MIDA', 'Imputed_Data')
    
    # Phase 4
    dot.edge('Imputed_Data', 'TrainVal')
    dot.edge('TrainVal', 'Models')
    
    dot.edge('Models', 'RSF')
    dot.edge('Models', 'XGB')
    dot.edge('Models', 'DS')
    dot.edge('Models', 'CWGB')
    
    # Phase 5
    dot.edge('RSF', 'Metrics')
    dot.edge('XGB', 'Metrics')
    dot.edge('DS', 'Metrics')
    dot.edge('CWGB', 'Metrics')
    
    dot.edge('Metrics', 'Perf')
    dot.edge('Metrics', 'Interpret')
    dot.edge('Metrics', 'Clinical')
    
    dot.edge('Perf', 'Conclusion')
    dot.edge('Interpret', 'Conclusion')
    dot.edge('Clinical', 'Conclusion')

    # ---------------------------------------------------------
    # External Bracket Labels for Phases 2-5
    # ---------------------------------------------------------
    
    # ---------------------------------------------------------
    # External Bracket Labels for Phases 2-5
    # ---------------------------------------------------------
    # To make edges start from clusters, we need compound=true
    dot.attr(compound='true', newrank='true')

    # ---------------------------------------------------------
    # External Arrow Labels for Phases 2-5
    # ---------------------------------------------------------
    # The user wants arrows pointing from the rectangular cluster to the label
    # e.g. [Cluster] ----> Label
    # We use 'ltail' to make the arrow start from the cluster boundary.
    
    # Phase 2 Label
    dot.node('Ph2_Label', 'Phase 2: Missing Data Simulation', shape='none', fontname='Helvetica', fontsize='16')
    # Use rank=same to align horizontally
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('Ph2_Label')
        # Edge from a node inside cluster_1 (SimGen) to external label
        # ltail='cluster_1' means the arrow starts from the cluster box
        # minlen keeps it pushed out a bit
        dot.edge('SimGen', 'Ph2_Label', ltail='cluster_1', minlen='2')

    # Phase 3 Label
    dot.node('Ph3_Label', 'Phase 3: Imputation', shape='none', fontname='Helvetica', fontsize='16')
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('Ph3_Label')
        # Node inside cluster_2 is ImpStart
        dot.edge('ImpStart', 'Ph3_Label', ltail='cluster_2', minlen='2')

    # Phase 4 Label
    dot.node('Ph4_Label', 'Phase 4: Machine Learning Modeling', shape='none', fontname='Helvetica', fontsize='16')
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('Ph4_Label')
        # Node inside cluster_3 is TrainVal
        dot.edge('TrainVal', 'Ph4_Label', ltail='cluster_3', minlen='2')

    # Phase 5 Label
    dot.node('Ph5_Label', 'Phase 5: Performance & Analysis', shape='none', fontname='Helvetica', fontsize='16')
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('Ph5_Label')
        # Node inside cluster_4 is Metrics
        dot.edge('Metrics', 'Ph5_Label', ltail='cluster_4', minlen='2')

    output_path = 'methodology_flowchart'
    dot.render(output_path, view=False)
    print(f"Flowchart saved to {output_path}.png")

if __name__ == '__main__':
    create_flowchart()
