import tools_registry

def test_tools_count():
    assert len(tools_registry.TOOLS_REGISTRY) == 13, "Existem exatamente 13 tools mapeadas"

def test_tools_structure():
    for tool in tools_registry.TOOLS_REGISTRY:
        assert tool.get("type") == "function"
        
        func = tool.get("function", {})
        assert "name" in func
        assert "description" in func
        assert "parameters" in func
        
        schema = func["parameters"]
        assert schema.get("type") == "object"

def test_tools_required_params():
    for tool in tools_registry.TOOLS_REGISTRY:
        func = tool["function"]
        schema = func["parameters"]
        
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        for req in required:
            # Garante que todo required parameter da tool foi decrito em properties
            assert req in properties, f"Parâmetro requerido '{req}' não definido nas properties da tool '{func['name']}'"
