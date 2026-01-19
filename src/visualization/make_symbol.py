
import matplotlib.pyplot as plt
import numpy as np
import random

def create_data_science_symbol():
    # Setup the figure
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(-2, 12)
    ax.set_ylim(-2, 12)
    ax.axis('off')  # Turn off axes

    # Define Node Layers (Neural Network Style)
    # Coordinates: (x, y)
    layers = {
        0: [(2, 2), (2, 5), (2, 8)],      # Input layer
        1: [(5, 1), (5, 3.5), (5, 6.5), (5, 9)], # Hidden layer
        2: [(8, 2), (8, 5), (8, 8)]       # Output layer
    }

    # Draw Connections (Edges)
    # Connect every node in layer i to every node in layer i+1
    for i in range(2):
        for start_node in layers[i]:
            for end_node in layers[i+1]:
                # Randomize alpha for "active" look
                alpha = random.uniform(0.1, 0.4)
                ax.plot([start_node[0], end_node[0]], [start_node[1], end_node[1]], 
                        c='#0077be', lw=1.5, alpha=alpha, zorder=1)

    # Draw Nodes
    for layer_idx, nodes in layers.items():
        x_vals = [n[0] for n in nodes]
        y_vals = [n[1] for n in nodes]
        
        # Color gradient based on layer
        if layer_idx == 0: color = '#004c6d' # Dark Blue
        elif layer_idx == 1: color = '#0077be' # Medium Blue
        else: color = '#00a0c6' # Teal

        ax.scatter(x_vals, y_vals, s=600, c=color, edgecolors='white', linewidth=2, zorder=2)

    # Add Data/Math Symbols floating around
    symbols = [
        (r'$\Sigma$', (3.5, 7.5)),
        (r'$\int$', (6.5, 3)),
        (r'$\pi$', (3.5, 2.5)),
        ('0', (6.5, 8.5)),
        ('1', (4, 4.5)),
        ('1', (7, 6)),
        ('0', (9, 4))
    ]

    for sym, pos in symbols:
        ax.text(pos[0], pos[1], sym, fontsize=18, color='#004c6d', alpha=0.7, 
                ha='center', va='center', fontname='DejaVu Sans')

    # Save as SVG
    output_file = "data_science_symbol_vector.svg"
    plt.tight_layout()
    plt.savefig(output_file, format='svg', transparent=True, bbox_inches='tight')
    print(f"Successfully generated: {output_file}")

if __name__ == "__main__":
    create_data_science_symbol()
