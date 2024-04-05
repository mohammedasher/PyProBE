import streamlit as st
import os
import pandas as pd
import pickle
import sys
import plotly.graph_objects as go
import plotly

import pandas as pd
# Add the parent directory of pybatdata to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

with open('procedure_dict.pkl', 'rb') as f:
    procedure_dict = pickle.load(f)

metadata = pd.DataFrame(procedure_dict).drop('Data', axis=1)
def dataframe_with_selections(df):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.sidebar.data_editor(
        df_with_selections,
        hide_index=True,  # Keep the index visible
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_rows = edited_df[edited_df.Select]
    selected_indices = selected_rows.index.tolist()  # Get the indices of the selected rows
    return selected_indices

# Display the DataFrame in the sidebar
selected_indices = dataframe_with_selections(metadata)
# Get the names of the selected rows
selected_names = [procedure_dict[i]['Name'] for i in selected_indices]

# Select an experiment
experiment_names = procedure_dict[0]['Data'].titles.keys()
selected_experiment = st.sidebar.selectbox('Select an experiment', experiment_names)

# Get the cycle and step numbers from the user
cycle_step_input = st.sidebar.text_input('Enter the cycle and step numbers (e.g., "cycle(1).step(2)")')
x_options = ['Time (s)', 'Capacity (Ah)']
y_options = ['Voltage (V)', 'Current (A)', 'Capacity (Ah)']

graph_placeholder = st.empty()

col1, col2, col3 = st.columns(3)
# Create select boxes for the x and y axes
x_axis = col1.selectbox('x axis', x_options, index=0)
y_axis = col2.selectbox('y axis', y_options, index=1)
secondary_y_axis = col3.selectbox('Secondary y axis', ['None'] + y_options, index=0)

# Select plot theme

themes = list(plotly.io.templates)
themes.remove('none')
themes.remove('streamlit')
themes.insert(0, 'default')
plot_theme = st.selectbox('Plot theme', themes)

# Create a figure
fig = go.Figure()
selected_data = []
for i in range(len(selected_indices)):
    selected_index = selected_indices[i]
    experiment_data = procedure_dict[selected_index]['Data'].experiment(selected_experiment)
    # Check if the input is not empty
    if cycle_step_input:
        # Use eval to evaluate the input as Python code
        filtered_data = eval(f'experiment_data.{cycle_step_input}')
    else: 
        filtered_data = experiment_data
    
    filtered_data = filtered_data.RawData.to_pandas()
    selected_data.append(filtered_data)
    # Add a line to the plot for each selected index
    fig.add_trace(go.Scatter(x=filtered_data[x_axis], 
                             y=filtered_data[y_axis], 
                             mode='lines', 
                             line = dict(color = procedure_dict[selected_index]['Color']),
                             name=procedure_dict[selected_index]['Name'],
                             yaxis='y1',
                             showlegend=True))
    
    # Add a line to the secondary y axis if selected
    if secondary_y_axis != 'None':
        fig.add_trace(go.Scatter(x=filtered_data[x_axis], 
                                 y=filtered_data[secondary_y_axis], 
                                 mode='lines', 
                                 line=dict(color=procedure_dict[selected_index]['Color'], dash='dash'),
                                 name=procedure_dict[selected_index]['Name'],
                                 yaxis='y2',
                                 showlegend=False))
if secondary_y_axis != 'None':     
    # Add a dummy trace to the legend to represent the secondary y-axis
    fig.add_trace(go.Scatter(x=[None], 
                            y=[None], 
                            mode='lines', 
                            line=dict(color='black', dash='dash'),
                            name=secondary_y_axis,
                            showlegend=True))

# Set the plot's title and labels
fig.update_layout(xaxis_title=x_axis, 
                  yaxis_title=y_axis,
                  yaxis2 = dict(title=secondary_y_axis,
                                anchor='free',
                                overlaying='y',
                                autoshift=True,
                                tickmode='sync'),
                  template=plot_theme if plot_theme != 'default' else 'plotly',
                  legend = dict(x=1.2 if secondary_y_axis != 'None' else 1,
                                y = 1))

if secondary_y_axis != 'None':
    fig.update_layout(yaxis2=dict(title=secondary_y_axis, overlaying='y', side='right'))

# Show the plot
graph_placeholder.plotly_chart(fig, theme='streamlit' if plot_theme == 'default' else None)  

from bokeh.plotting import figure
from bokeh.models import LinearAxis, Range1d, DataRange1d

# Create a figure with a primary y-axis that auto-scales
p = figure(x_axis_label=x_axis, y_axis_label=y_axis)

def get_axis_range(data):
    min_value = data.min()
    max_value = data.max()
    range_value = max_value - min_value
    return min_value - 0.05 * range_value, max_value + 0.05 * range_value

selected_data = []
for i in range(len(selected_indices)):
    selected_index = selected_indices[i]
    experiment_data = procedure_dict[selected_index]['Data'].experiment(selected_experiment)
    # Check if the input is not empty
    if cycle_step_input:
        # Use eval to evaluate the input as Python code
        filtered_data = eval(f'experiment_data.{cycle_step_input}')
    else: 
        filtered_data = experiment_data
    
    filtered_data = filtered_data.RawData.to_pandas()
    selected_data.append(filtered_data)
    # Add a line to the plot for each selected index
    p.line(x=filtered_data[x_axis], 
           y=filtered_data[y_axis], 
           line_color=procedure_dict[selected_index]['Color'],
           line_width=3,
           legend_label=procedure_dict[selected_index]['Name'])
    
    y_min, y_max = get_axis_range(filtered_data[y_axis])
    p.y_range = Range1d(start=y_min, end=y_max)
    # Add a line to the secondary y axis if selected
    if secondary_y_axis != 'None':
        # Create a secondary y-axis that auto-scales
        y2_min, y2_max = get_axis_range(filtered_data[secondary_y_axis])
        p.extra_y_ranges = {"secondary": Range1d(start=y2_min, end=y2_max)}
        p.add_layout(LinearAxis(y_range_name="secondary"), 'right')
        p.line(x=filtered_data[x_axis], 
               y=filtered_data[secondary_y_axis], 
               line_color=procedure_dict[selected_index]['Color'], 
               y_range_name="secondary",
               line_width=3,
               line_dash='4 4',
               legend_label=procedure_dict[selected_index]['Name'])

st.bokeh_chart(p, use_container_width=True)


# Show raw data in tabs
if selected_data:
    tabs = st.tabs(selected_names)
    columns = ['Time (s)', 'Cycle', 'Step', 'Current (A)', 'Voltage (V)', 'Capacity (Ah)']
    for tab in tabs:
        tab.dataframe(selected_data[tabs.index(tab)][columns], hide_index=True)
