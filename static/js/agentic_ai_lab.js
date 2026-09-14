/**
 * SkillPilot - Agentic AI Lab with Visual Workflow Designer
 * Uses Drawflow for visual node-based workflow creation
 */

let drawflowEditor = null;
let currentGeneratedWorkflow = null;
let blockTypes = {};
let selectedNodeId = null;

// Initialize Agentic AI Lab when tab is shown
document.addEventListener('DOMContentLoaded', () => {
    // Initialize when Agentic AI Lab tab is clicked
    const agenticTab = document.querySelector('[data-tab="agentic-ai-lab"]');
    if (agenticTab) {
        agenticTab.addEventListener('click', initAgenticAILab);
    }
    
    // Initialize orchestrator button
    const generateBtn = document.getElementById('generateWorkflowBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateWorkflow);
    }
    
    // Initialize action buttons
    const saveBtn = document.getElementById('saveWorkflowBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveWorkflow);
    }
    
    const executeBtn = document.getElementById('executeWorkflowBtn');
    if (executeBtn) {
        executeBtn.addEventListener('click', executeWorkflow);
    }
    
    const newBtn = document.getElementById('newWorkflowBtn');
    if (newBtn) {
        newBtn.addEventListener('click', createNewWorkflow);
    }
});

/**
 * Initialize Agentic AI Lab and Drawflow
 */
async function initAgenticAILab() {
    if (!drawflowEditor) {
        await initDrawflow();
        await loadBlockTypes();
    }
    await loadMyWorkflows();
}

/**
 * Initialize Drawflow visual editor
 */
async function initDrawflow() {
    const container = document.getElementById('drawflowCanvas');
    if (!container || drawflowEditor) return;
    
    drawflowEditor = new Drawflow(container);
    drawflowEditor.start();
    
    // Set up event listeners
    drawflowEditor.on('nodeSelected', (nodeId) => {
        selectedNodeId = nodeId;
        displayNodeProperties(nodeId);
    });
    
    drawflowEditor.on('nodeUnselected', () => {
        selectedNodeId = null;
        clearNodeProperties();
    });
    
    // Show the visual workflow section
    document.getElementById('visualWorkflowSection').style.display = 'block';
    
    console.log('Drawflow initialized successfully');
}

/**
 * Load block types from backend
 */
async function loadBlockTypes() {
    try {
        const response = await fetch('/api/agents/block-types');
        const data = await response.json();
        
        blockTypes = {};
        data.block_types.forEach(block => {
            blockTypes[block.type] = block;
        });
        
        renderBlockPalette(data.block_types);
    } catch (error) {
        console.error('Error loading block types:', error);
        showStatus('Failed to load block types', 'error');
    }
}

/**
 * Render block palette
 */
function renderBlockPalette(blocks) {
    const container = document.getElementById('blockTypesList');
    if (!container) return;
    
    const icons = {
        'variable': 'fa-database',
        'prompt_template': 'fa-file-alt',
        'ai_model': 'fa-robot',
        'text_transform': 'fa-text-height',
        'condition': 'fa-code-branch',
        'output': 'fa-flag-checkered'
    };
    
    container.innerHTML = blocks.map(block => `
        <div class="block-palette-item" 
             draggable="true" 
             data-block-type="${block.type}"
             style="background: #f8f9fa; padding: 10px; margin-bottom: 8px; border-radius: 4px; cursor: grab; border: 1px solid #e0e0e0;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fas ${icons[block.type] || 'fa-cube'}" style="color: #0366d6;"></i>
                <strong style="font-size: 12px;">${block.name}</strong>
            </div>
            <p style="font-size: 11px; color: #666; margin: 5px 0 0 0;">${block.description}</p>
        </div>
    `).join('');
    
    // Add drag event listeners
    container.querySelectorAll('.block-palette-item').forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
    });
    
    // Add drop zone to canvas
    const canvas = document.getElementById('drawflowCanvas');
    canvas.addEventListener('dragover', handleDragOver);
    canvas.addEventListener('drop', handleDrop);
}

/**
 * Handle drag start
 */
function handleDragStart(e) {
    e.dataTransfer.setData('blockType', e.target.closest('.block-palette-item').dataset.blockType);
}

/**
 * Handle drag over
 */
function handleDragOver(e) {
    e.preventDefault();
}

/**
 * Handle drop - add node to canvas
 */
function handleDrop(e) {
    e.preventDefault();
    const blockType = e.dataTransfer.getData('blockType');
    const block = blockTypes[blockType];
    
    if (!block) return;
    
    const rect = e.target.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    addNodeToCanvas(blockType, x, y);
}

/**
 * Add node to canvas
 */
function addNodeToCanvas(blockType, x = 100, y = 100, data = {}) {
    const block = blockTypes[blockType];
    if (!block) return null;
    
    const nodeId = `node_${Date.now()}`;
    const html = createNodeHTML(block, data);
    
    const inputCount = block.inputs.length;
    const outputCount = block.outputs.length;
    
    drawflowEditor.addNode(
        block.name,
        inputCount,
        outputCount,
        x,
        y,
        block.type,
        { ...data, blockType: blockType },
        html
    );
    
    return nodeId;
}

/**
 * Create node HTML
 */
function createNodeHTML(block, data = {}) {
    const icons = {
        'variable': 'fa-database',
        'prompt_template': 'fa-file-alt',
        'ai_model': 'fa-robot',
        'text_transform': 'fa-text-height',
        'condition': 'fa-code-branch',
        'output': 'fa-flag-checkered'
    };
    
    return `
        <div style="padding: 10px; min-width: 150px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <i class="fas ${icons[block.type] || 'fa-cube'}" style="color: #0366d6;"></i>
                <strong style="font-size: 13px;">${data.label || block.name}</strong>
            </div>
            <div style="font-size: 11px; color: #666;">
                ${data.summary || 'Configure in properties panel'}
            </div>
        </div>
    `;
}

/**
 * Display node properties in inspector
 */
function displayNodeProperties(nodeId) {
    const nodeData = drawflowEditor.getNodeFromId(nodeId);
    if (!nodeData) return;
    
    const block = blockTypes[nodeData.class];
    if (!block) return;
    
    const properties = nodeData.data || {};
    
    let html = `
        <div style="margin-bottom: 15px;">
            <strong style="color: #333;">${block.name}</strong>
            <p style="font-size: 12px; color: #666; margin: 5px 0;">${block.description}</p>
        </div>
    `;
    
    // Generate form fields based on block params
    if (block.type === 'variable') {
        html += `
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 12px; margin-bottom: 5px;">Variable Name</label>
                <input type="text" id="prop_name" value="${properties.name || ''}" 
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
            </div>
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 12px; margin-bottom: 5px;">Value</label>
                <input type="text" id="prop_value" value="${properties.value || ''}" 
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
            </div>
        `;
    } else if (block.type === 'prompt_template') {
        html += `
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 12px; margin-bottom: 5px;">Template</label>
                <textarea id="prop_template" rows="4" 
                          style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">${properties.template || ''}</textarea>
                <small style="font-size: 11px; color: #666;">Use {variable_name} for variables</small>
            </div>
        `;
    } else if (block.type === 'ai_model') {
        html += `
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 12px; margin-bottom: 5px;">Model</label>
                <select id="prop_model" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
                    <option value="gpt-5.6-terra" ${properties.model === 'gpt-5.6-terra' ? 'selected' : ''}>GPT-5.6 Terra</option>
                    <option value="gpt-5.6-luna" ${properties.model === 'gpt-5.6-luna' ? 'selected' : ''}>GPT-5.6 Luna (fast)</option>
                    <option value="claude-sonnet-5" ${properties.model === 'claude-sonnet-5' ? 'selected' : ''}>Claude Sonnet 5</option>
                    <option value="gemini-3.8-flash" ${properties.model === 'gemini-3.8-flash' ? 'selected' : ''}>Gemini 3.8 Flash</option>
                </select>
            </div>
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 12px; margin-bottom: 5px;">Prompt</label>
                <textarea id="prop_prompt" rows="4" 
                          style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">${properties.prompt || ''}</textarea>
            </div>
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 12px; margin-bottom: 5px;">Temperature: ${properties.temperature || 0.7}</label>
                <input type="range" id="prop_temperature" min="0" max="1" step="0.1" value="${properties.temperature || 0.7}" 
                       style="width: 100%;">
            </div>
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 12px; margin-bottom: 5px;">Max Tokens</label>
                <input type="number" id="prop_max_tokens" value="${properties.max_tokens || 2000}" 
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
            </div>
        `;
    } else if (block.type === 'output') {
        html += `
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 12px; margin-bottom: 5px;">Output Label</label>
                <input type="text" id="prop_label" value="${properties.label || 'Output'}" 
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px;">
            </div>
        `;
    }
    
    html += `
        <button onclick="updateNodeProperties()" 
                style="width: 100%; padding: 10px; background: #0366d6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;">
            <i class="fas fa-check"></i> Apply Changes
        </button>
    `;
    
    document.getElementById('nodeProperties').innerHTML = html;
}

/**
 * Update node properties
 */
function updateNodeProperties() {
    if (!selectedNodeId) return;
    
    const nodeData = drawflowEditor.getNodeFromId(selectedNodeId);
    if (!nodeData) return;
    
    const block = blockTypes[nodeData.class];
    const updatedData = { ...nodeData.data };
    
    // Collect form values
    const formInputs = document.querySelectorAll('#nodeProperties input, #nodeProperties select, #nodeProperties textarea');
    formInputs.forEach(input => {
        const propName = input.id.replace('prop_', '');
        updatedData[propName] = input.type === 'number' ? parseFloat(input.value) : input.value;
    });
    
    // Update node data
    drawflowEditor.updateNodeDataFromId(selectedNodeId, updatedData);
    
    // Update node HTML
    const newHTML = createNodeHTML(block, updatedData);
    const nodeElement = document.getElementById(`node-${selectedNodeId}`);
    if (nodeElement) {
        const contentElement = nodeElement.querySelector('.drawflow_content_node');
        if (contentElement) {
            contentElement.innerHTML = newHTML;
        }
    }
    
    showStatus('Node properties updated', 'success');
}

/**
 * Clear node properties
 */
function clearNodeProperties() {
    document.getElementById('nodeProperties').innerHTML = `
        <div style="color: #999; text-align: center; padding: 20px 0;">
            Select a node to edit properties
        </div>
    `;
}

/**
 * Generate AI Workflow using Orchestrator
 */
async function generateWorkflow() {
    const promptInput = document.getElementById('orchestratorPrompt');
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        showStatus('Please describe what you want to accomplish', 'error');
        return;
    }
    
    const generateBtn = document.getElementById('generateWorkflowBtn');
    const originalBtnText = generateBtn.innerHTML;
    
    try {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating Workflow...';
        showStatus('AI Orchestrator is analyzing your request and creating specialized agents...', 'info');
        
        const response = await fetch('/api/agents/orchestrate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to generate workflow');
        }
        
        currentGeneratedWorkflow = data.workflow;
        
        // Display workflow visually on canvas
        displayWorkflowOnCanvas(data.workflow);
        showStatus(data.message + ' - Workflow displayed on canvas', 'success');
        
    } catch (error) {
        console.error('Error generating workflow:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = originalBtnText;
    }
}

/**
 * Display workflow on visual canvas
 */
function displayWorkflowOnCanvas(workflow) {
    // Clear existing canvas
    if (drawflowEditor) {
        drawflowEditor.clear();
    }
    
    // Show visual workflow section
    document.getElementById('visualWorkflowSection').style.display = 'block';
    document.getElementById('workflowTitle').textContent = workflow.name || 'Generated Workflow';
    
    // Add nodes from workflow blocks
    const nodeIdMap = {};
    workflow.blocks.forEach((block, index) => {
        const x = block.position?.x || 100 + (index * 200);
        const y = block.position?.y || 100 + (Math.floor(index / 3) * 150);
        
        const html = createNodeHTML(blockTypes[block.type] || { name: block.label || block.type, type: block.type }, block.params || {});
        
        const nodeId = drawflowEditor.addNode(
            block.label || block.name || block.type,
            1, // inputs
            1, // outputs
            x,
            y,
            block.type,
            { ...block.params, blockType: block.type },
            html
        );
        
        nodeIdMap[block.id] = nodeId;
    });
    
    // Add connections
    if (workflow.connections && Array.isArray(workflow.connections)) {
        workflow.connections.forEach(conn => {
            const fromNode = nodeIdMap[conn.from_block];
            const toNode = nodeIdMap[conn.to_block];
            
            if (fromNode && toNode) {
                drawflowEditor.addConnection(fromNode, toNode, 'output_1', 'input_1');
            }
        });
    }
    
    currentGeneratedWorkflow = workflow;
}

/**
 * Create new workflow
 */
function createNewWorkflow() {
    if (drawflowEditor) {
        drawflowEditor.clear();
    }
    currentGeneratedWorkflow = null;
    document.getElementById('workflowTitle').textContent = 'New Workflow';
    showStatus('New workflow created', 'info');
}

/**
 * Save workflow
 */
async function saveWorkflow() {
    if (!drawflowEditor) return;
    
    const exportData = drawflowEditor.export();
    const nodes = exportData.drawflow.Home.data;
    
    if (Object.keys(nodes).length === 0) {
        showStatus('No workflow to save. Add some blocks first!', 'error');
        return;
    }
    
    const workflowName = document.getElementById('workflowTitle').textContent || 'Untitled Workflow';
    
    // Convert Drawflow format to backend format
    const blocks = [];
    const connections = [];
    
    Object.keys(nodes).forEach(nodeId => {
        const node = nodes[nodeId];
        blocks.push({
            id: `block_${nodeId}`,
            type: node.class,
            label: node.name,
            params: node.data,
            position: { x: node.pos_x, y: node.pos_y }
        });
        
        // Extract connections
        Object.keys(node.outputs).forEach(outputKey => {
            const output = node.outputs[outputKey];
            output.connections.forEach(conn => {
                connections.push({
                    from_block: `block_${nodeId}`,
                    from_output: outputKey,
                    to_block: `block_${conn.node}`,
                    to_input: conn.output
                });
            });
        });
    });
    
    const workflow = {
        name: workflowName,
        description: currentGeneratedWorkflow?.description || 'Custom workflow',
        blocks: blocks,
        connections: connections
    };
    
    try {
        const response = await fetch('/api/agents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(workflow)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to save workflow');
        }
        
        showStatus('Workflow saved successfully!', 'success');
        await loadMyWorkflows();
        
    } catch (error) {
        console.error('Error saving workflow:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
}

/**
 * Execute workflow
 */
async function executeWorkflow() {
    if (!currentGeneratedWorkflow && !drawflowEditor) return;
    
    let workflowToExecute;
    
    if (drawflowEditor) {
        // Convert current canvas to workflow
        const exportData = drawflowEditor.export();
        const nodes = exportData.drawflow.Home.data;
        
        const blocks = [];
        const connections = [];
        
        Object.keys(nodes).forEach(nodeId => {
            const node = nodes[nodeId];
            blocks.push({
                id: `block_${nodeId}`,
                type: node.class,
                label: node.name,
                params: node.data,
                position: { x: node.pos_x, y: node.pos_y }
            });
            
            Object.keys(node.outputs).forEach(outputKey => {
                const output = node.outputs[outputKey];
                output.connections.forEach(conn => {
                    connections.push({
                        from_block: `block_${nodeId}`,
                        from_output: outputKey,
                        to_block: `block_${conn.node}`,
                        to_input: conn.output
                    });
                });
            });
        });
        
        workflowToExecute = {
            blocks: blocks,
            connections: connections
        };
    } else {
        workflowToExecute = currentGeneratedWorkflow;
    }
    
    const executeBtn = document.getElementById('executeWorkflowBtn');
    const originalBtnText = executeBtn.innerHTML;
    
    try {
        executeBtn.disabled = true;
        executeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Executing...';
        showStatus('Executing AI workflow...', 'info');
        
        const response = await fetch('/api/agents/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ workflow: workflowToExecute })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Execution failed');
        }
        
        displayExecutionResults(data);
        showStatus('Workflow executed successfully!', 'success');
        
    } catch (error) {
        console.error('Error executing workflow:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        executeBtn.disabled = false;
        executeBtn.innerHTML = originalBtnText;
    }
}

/**
 * Display execution results
 */
function displayExecutionResults(results) {
    const resultsDiv = document.getElementById('executionResults');
    resultsDiv.style.display = 'block';
    
    let html = `
        <div style="background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 20px; margin-top: 20px;">
            <h4><i class="fas fa-check-circle" style="color: #22c55e;"></i> Execution Results</h4>
    `;
    
    if (results.outputs && results.outputs.length > 0) {
        html += '<div style="margin-top: 15px;"><strong>Outputs:</strong></div>';
        results.outputs.forEach(output => {
            html += `
                <div style="background: #f8f9fa; padding: 15px; margin-top: 10px; border-radius: 6px; border-left: 4px solid #22c55e;">
                    <strong>${output.label}</strong>
                    <pre style="margin-top: 8px; white-space: pre-wrap; font-size: 13px;">${output.content}</pre>
                </div>
            `;
        });
    }
    
    if (results.execution_log && results.execution_log.length > 0) {
        html += '<div style="margin-top: 20px;"><strong>Execution Log:</strong></div>';
        results.execution_log.forEach(log => {
            const levelColor = log.level === 'error' ? '#ef4444' : log.level === 'warning' ? '#f59e0b' : '#666';
            html += `
                <div style="font-size: 12px; color: ${levelColor}; margin-top: 5px;">
                    [${new Date(log.timestamp).toLocaleTimeString()}] ${log.message}
                </div>
            `;
        });
    }
    
    html += '</div>';
    resultsDiv.innerHTML = html;
}

/**
 * Load my workflows
 */
async function loadMyWorkflows() {
    try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        
        const container = document.getElementById('myWorkflowsList');
        if (!container) return;
        
        if (!data.agents || data.agents.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <i class="fas fa-inbox" style="font-size: 48px; opacity: 0.3;"></i>
                    <p style="margin-top: 16px;">No workflows saved yet</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.agents.map(workflow => `
            <div class="workflow-card" data-testid="card-workflow-${workflow.agent_id}" 
                 style="background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 6px; border-left: 4px solid #0366d6; cursor: pointer;"
                 onclick="loadWorkflow('${workflow.agent_id}')">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <strong style="color: #333;">${escapeHtml(workflow.name)}</strong>
                        <p style="color: #666; font-size: 13px; margin: 5px 0;">${escapeHtml(workflow.description || '')}</p>
                        <small style="color: #999;">
                            ${workflow.blocks ? workflow.blocks.length : 0} blocks • 
                            Created: ${new Date(workflow.created_at).toLocaleDateString()}
                        </small>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button onclick="event.stopPropagation(); executeExistingWorkflow('${workflow.agent_id}')" 
                                class="btn-icon" title="Execute" data-testid="button-execute-${workflow.agent_id}">
                            <i class="fas fa-play"></i>
                        </button>
                        <button onclick="event.stopPropagation(); deleteWorkflow('${workflow.agent_id}')" 
                                class="btn-icon" title="Delete" data-testid="button-delete-${workflow.agent_id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading workflows:', error);
        showStatus('Failed to load workflows', 'error');
    }
}

/**
 * Load workflow onto canvas
 */
async function loadWorkflow(workflowId) {
    try {
        const response = await fetch(`/api/agents/${workflowId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load workflow');
        }
        
        displayWorkflowOnCanvas(data.agent);
        showStatus('Workflow loaded successfully!', 'success');
        
    } catch (error) {
        console.error('Error loading workflow:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
}

/**
 * Execute existing workflow
 */
async function executeExistingWorkflow(workflowId) {
    try {
        const response = await fetch(`/api/agents/${workflowId}/execute`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Execution failed');
        }
        
        displayExecutionResults(data);
        showStatus('Workflow executed successfully!', 'success');
        
    } catch (error) {
        console.error('Error executing workflow:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
}

/**
 * Delete workflow
 */
async function deleteWorkflow(workflowId) {
    if (!confirm('Are you sure you want to delete this workflow?')) return;
    
    try {
        const response = await fetch(`/api/agents/${workflowId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete workflow');
        }
        
        showStatus('Workflow deleted successfully!', 'success');
        await loadMyWorkflows();
        
    } catch (error) {
        console.error('Error deleting workflow:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
}

/**
 * Show status message
 */
function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('workflowStatus');
    if (!statusDiv) return;
    
    const colors = {
        'info': '#0ea5e9',
        'success': '#22c55e',
        'error': '#ef4444',
        'warning': '#f59e0b'
    };
    
    statusDiv.style.display = 'block';
    statusDiv.style.padding = '15px';
    statusDiv.style.borderRadius = '8px';
    statusDiv.style.backgroundColor = colors[type] + '20';
    statusDiv.style.color = colors[type];
    statusDiv.style.border = `1px solid ${colors[type]}`;
    statusDiv.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}`;
    
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text ? text.replace(/[&<>"']/g, m => map[m]) : '';
}
