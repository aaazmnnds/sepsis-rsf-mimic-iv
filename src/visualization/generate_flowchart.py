from graphviz import Digraph

def create_flowchart():
    dot = Digraph(comment='Study Methodology', format='png')
    # rankdir='TB' (Top to Bottom)
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

    # CLUSTERS: User requested NO grey shadows background.
    # We remove 'filled' and 'fillcolor'. We keep 'rounded' for shape.
    cluster_attr = {'style': 'rounded', 'color': 'black', 'margin': '25', 'labeljust': 'c'}

    # ---------------------------------------------------------
    # Phase 1: Data Acquisition
    with dot.subgraph(name='cluster_0') as c:
        # User requested Phase 1 Label to be outside for consistency.
        # So we remove the label from the cluster attribute.
        c.attr(label='', **cluster_attr)
        
        with c.subgraph() as header:
            header.attr(rank='same')
            header.node('MIMIC', 'MIMIC-IV\n(Primary Dataset)\nn=852', fillcolor=c_primary, shape='cylinder', group='main_left')
            header.node('SIM', 'Simulated Cohort\n(Method Validation)\nn=852', fillcolor=c_secondary, shape='cylinder', group='main_right')
            
            # Invisible edge to define left-to-right relation
            header.edge('MIMIC', 'SIM', style='invis', weight='50')

    # ---------------------------------------------------------
    # Phase 2: Missing Data
    with dot.subgraph(name='cluster_1') as c:
        c.attr(**cluster_attr)
        
        with c.subgraph() as level2:
            level2.attr(rank='same')
            # Observed Missing Data -> Left Group
            level2.node('MIMIC_Miss', 'Observed Missing Data', fillcolor='#ffffff', group='main_left')
            
            # SimGen -> Right Group
            level2.node('SimGen', 'Missing Mechanisms', shape='diamond', fillcolor='#ffffff', group='main_right')
            
            # Constraint: Left to Right
            level2.edge('MIMIC_Miss', 'SimGen', style='invis', weight='50')
        
        c.node('MCAR', 'MCAR', fillcolor=c_process)
        c.node('MAR', 'MAR', fillcolor=c_process)
        c.node('MNAR', 'MNAR', fillcolor=c_process)
        
        c.edge('SimGen', 'MCAR')
        c.edge('SimGen', 'MAR')
        c.edge('SimGen', 'MNAR')

    # ---------------------------------------------------------
    # Phase 3: Imputation
    with dot.subgraph(name='cluster_2') as c:
        c.attr(**cluster_attr)
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
    # ---------------------------------------------------------
    # Phase 4: Modeling
    with dot.subgraph(name='cluster_3') as c:
        c.attr(**cluster_attr)
        c.node('Imputed_Data', 'Complete Imputed Datasets', fillcolor=c_process)
        
        # Reverting to standard label with explicit formatting to fix "erased" artifact.
        # Increased margin and using strict rectangular shape.
        # Using HTML-like label to prevent text clipping ("erased" look) while keeping box size reasonable
        c.node('TrainVal', '<Model Training and Validation<br/>Split (90/10), 10-Fold CV, Preprocessing>', 
               fillcolor='#ffffff', shape='rect', margin='0.2', fontsize='12')
        
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
        c.attr(**cluster_attr)
        c.node('Metrics', 'Evaluation', shape='diamond', fillcolor='#ffffff')
        
        with c.subgraph() as outputs:
            outputs.attr(rank='same')
            outputs.node('Perf', 'Performance Metrics\n- C-index\n- IBS\n- Time-dependent AUC', fillcolor=c_primary)
            outputs.node('Interpret', 'Interpretability', fillcolor=c_secondary)
            outputs.node('Clinical', 'Clinical Utility', fillcolor=c_secondary)

    dot.node('Conclusion', 'Final Conclusion\n& Recommendation', shape='note', fillcolor='#ffffcc')

    # ---------------------------------------------------------
    # EDGES (Process Flow)
    # ---------------------------------------------------------
    
    # Phase 1 -> Phase 2
    dot.edge('MIMIC', 'MIMIC_Miss', label='Assess Missingness', weight='10')
    dot.edge('SIM', 'SimGen', label='Amputation', weight='10')
    
    # Phase 2 -> Phase 3
    dot.edge('MIMIC_Miss', 'ImpStart')
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
    # EXTERNAL PHASE LABELS (No Arrows, Consistent Format)
    # ---------------------------------------------------------
    
    # To keep labels aligned with their phases, we use invisible edges and subgraphs.
    dot.attr(compound='true', newrank='true')

    label_font = {'shape': 'none', 'fontname': 'Helvetica-Bold', 'fontsize': '16'}

    # ---------------------------------------------------------
    # RIGHT SIDE PHASE FLOWCHART
    # ---------------------------------------------------------
    # Create a vertical chain of rectangular blocks for Phases 1-5 + Conclusion
    # They will be aligned to the right of the main content
    
    with dot.subgraph(name='cluster_phases') as p:
        p.attr(style='invis') # Invisible container for the phase column
        
        # Define Phase Nodes (Rectangular Blocks)
        # Using HTML labels for bold title + consistent sizing if needed, or just standard strings with box shape
        phase_node_attr = {'shape': 'box', 'style': 'filled', 'fillcolor': '#eeeeee', 'fontname': 'Helvetica-Bold', 'fontsize': '12', 'width': '1.8', 'fixedsize': 'false'}
        
        p.node('Ph1', 'Phase 1\nData Acquisition', **phase_node_attr, group='phase_col')
        p.node('Ph2', 'Phase 2\nMissing Data Simulation', **phase_node_attr, group='phase_col')
        p.node('Ph3', 'Phase 3\nImputation', **phase_node_attr, group='phase_col')
        p.node('Ph4', 'Phase 4\nMachine Learning Modeling', **phase_node_attr, group='phase_col')
        p.node('Ph5', 'Phase 5\nPerformance & Analysis', **phase_node_attr, group='phase_col')
        
        # Override fillcolor for Conclusion
        # We need to copy attr and update, or just pass individual args to avoid collision if **kwargs has it
        conc_attr = phase_node_attr.copy()
        conc_attr['fillcolor'] = '#ffffcc'
        p.node('PhConc', 'Final Conclusion\n& Recommendation', **conc_attr, group='phase_col')
        
        # Connect them downwards
        p.edge('Ph1', 'Ph2', weight='100')
        p.edge('Ph2', 'Ph3', weight='100')
        p.edge('Ph3', 'Ph4', weight='100')
        p.edge('Ph4', 'Ph5', weight='100')
        p.edge('Ph5', 'PhConc', weight='100')

    # Remove the old Conclusion node if it exists elsewhere or repurpose it
    # note: We defined 'Conclusion' earlier in the main script (line 115). 
    # We should remove that one or aliasing it.
    # The user wants "Final Conclusion" in this vertical flow.
    # So we used 'PhConc' above. We will remove the old 'Conclusion' node definition from line 115 if possible or just ignore it.
    # Actually, line 115 `dot.node('Conclusion'...)` is outside the clusters. 
    # The edges in the main graph pointed to 'Conclusion'. We need to redirect them to 'PhConc' or align 'Conclusion' with 'PhConc'.
    # Simpler: Make 'PhConc' THE conclusion node or link to it.
    # But the main flow (Metrics -> Conclusion) implies the conclusion is the result of the process.
    # The user says "on the right side... Phase 1... Final conclusion".
    # This suggests the Phase Column TRACKS the process.
    # So 'PhConc' is the Label for the Conclusion step.
    # Is there a content node for Conclusion? 
    # "Final Conclusion and Recommendation is not Phase 5".
    # Let's assume the Phase Column IS the structure/outline.
    # Content flows on left. Phase labels flow on right.
    
    # ALIGNMENT (Content <-> Phase Column)
    
    # rank=same for Top of Content <-> Phase Node
    
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('MIMIC')
        s.node('Ph1')

    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('MIMIC_Miss') # Top of Phase 2
        s.node('Ph2')
        
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('ImpStart') # Top of Phase 3
        s.node('Ph3')
        
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('Imputed_Data') # Top of Phase 4
        s.node('Ph4')

    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('Metrics') # Top of Phase 5
        s.node('Ph5')
        
    # Align Conclusion content (if any) with PhConc?
    # The main graph had 'Conclusion' node. Let's make that node align with PhConc.
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('Conclusion')
        s.node('PhConc')

    # Link Content to Phase Column? (Optional, user didn't ask for arrows between them, just "flowchart downward")
    # We maintain separation.
    
    # Ensure Right Alignment
    # We can use an invisible edge from a right-most node of content to the phase node to force left-to-right ordering
    dot.edge('SIM', 'Ph1', style='invis', minlen='3')
    
    output_path = 'methodology_flowchart'
    dot.render(output_path, view=False)
    print(f"Flowchart saved to {output_path}.png")

if __name__ == '__main__':
    create_flowchart()
