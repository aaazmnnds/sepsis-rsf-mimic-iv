from graphviz import Digraph

def create_missing_imputation_diagram():
    dot = Digraph(comment='Missing Data and Imputation Architecture', format='png')
    dot.attr(rankdir='TB', splines='ortho', nodesep='0.5', ranksep='0.8')

    # Styling
    dot.attr('node', fontname='Helvetica', fontsize='11', shape='box', style='rounded,filled')
    dot.attr('edge', fontname='Helvetica', fontsize='9')

    # Colors
    c_data = '#e3f2fd'        # Light blue - data
    c_mechanism = '#fff3e0'   # Light orange - mechanisms
    c_imputation = '#e8f5e9'  # Light green - imputation
    c_output = '#f3e5f5'      # Light purple - output

    # Complete Dataset
    dot.node('Complete', 'Complete Synthetic Dataset\nn=852, No Missing Values',
             fillcolor=c_data, shape='cylinder', width='3')

    # Missing Data Mechanisms (same rank)
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('MCAR', 'MCAR\n(Random\nMissingness)', fillcolor=c_mechanism, width='1.5')
        s.node('MAR', 'MAR\n(Depends on\nObserved Data)', fillcolor=c_mechanism, width='1.5')
        s.node('MNAR', 'MNAR\n(Depends on\nUnobserved Data)', fillcolor=c_mechanism, width='1.5')

    # Incomplete datasets
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('Inc_MCAR', 'Incomplete\nDataset\n(MCAR)', fillcolor='#ffebee', width='1.5')
        s.node('Inc_MAR', 'Incomplete\nDataset\n(MAR)', fillcolor='#ffebee', width='1.5')
        s.node('Inc_MNAR', 'Incomplete\nDataset\n(MNAR)', fillcolor='#ffebee', width='1.5')

    # Imputation Methods Label
    dot.node('ImpLabel', 'Imputation Methods Applied to Each Dataset:',
             fillcolor='white', shape='plaintext', fontsize='10', fontname='Helvetica-Bold')

    # Imputation Methods (same rank)
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('MICE', 'MICE\n(Statistical)', fillcolor=c_imputation, width='1.3')
        s.node('MF', 'missForest\n(Ensemble)', fillcolor=c_imputation, width='1.3')
        s.node('GAIN', 'GAIN\n(GAN)', fillcolor=c_imputation, width='1.3')
        s.node('MIDA', 'MIDA\n(Autoencoder)', fillcolor=c_imputation, width='1.3')

    # Complete Imputed Datasets
    dot.node('Imputed', 'Complete Imputed Datasets\nReady for ML Modeling',
             fillcolor=c_output, shape='cylinder', width='3')

    # Edges - Complete to Mechanisms
    dot.edge('Complete', 'MCAR', label='Amputation')
    dot.edge('Complete', 'MAR', label='Amputation')
    dot.edge('Complete', 'MNAR', label='Amputation')

    # Mechanisms to Incomplete
    dot.edge('MCAR', 'Inc_MCAR')
    dot.edge('MAR', 'Inc_MAR')
    dot.edge('MNAR', 'Inc_MNAR')

    # Incomplete to Imputation Label
    dot.edge('Inc_MCAR', 'ImpLabel', style='invis')
    dot.edge('Inc_MAR', 'ImpLabel', style='invis')
    dot.edge('Inc_MNAR', 'ImpLabel', style='invis')

    # Label to Methods
    dot.edge('ImpLabel', 'MICE', style='invis')
    dot.edge('ImpLabel', 'MF', style='invis')
    dot.edge('ImpLabel', 'GAIN', style='invis')
    dot.edge('ImpLabel', 'MIDA', style='invis')

    # Methods to Final Output
    dot.edge('MICE', 'Imputed')
    dot.edge('MF', 'Imputed')
    dot.edge('GAIN', 'Imputed')
    dot.edge('MIDA', 'Imputed')

    # Add note
    dot.node('Note', '3 Mechanisms × 4 Imputation Methods = 12 Complete Datasets',
             fillcolor='#fffde7', shape='note', fontsize='9', style='filled')
    dot.edge('Imputed', 'Note', style='dashed', arrowhead='none')

    output_path = 'missing_imputation_architecture'
    dot.render(output_path, view=False)
    print(f"Diagram saved to {output_path}.png")

if __name__ == '__main__':
    create_missing_imputation_diagram()