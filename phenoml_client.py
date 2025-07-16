import requests
import json
import os
from typing import Dict, Optional, List

# uncomment the following lines if you're running locally
# from dotenv import load_dotenv

# Load environment variables from .env file
# load_dotenv()

# # Configuration
# BASE_URL = os.getenv("PHENOML_BASE_URL", "")
# EMAIL = os.getenv("PHENOML_EMAIL", "")
# PASSWORD = os.getenv("PHENOML_PASSWORD", "")

# Get environment variables from Google Colab userdata
from google.colab import userdata
BASE_URL = userdata.get('PHENOML_BASE_URL')
EMAIL = userdata.get('PHENOML_EMAIL')
PASSWORD = userdata.get('PHENOML_PASSWORD')


class PhenoMLClient:
    """Simple client for PhenoML API interactions"""
    
    def __init__(self, base_url: str = BASE_URL, email: str = EMAIL, password: str = PASSWORD):
        self.token = None
        self.base_url = base_url
        self.email = email
        self.password = password
        
    def authenticate(self) -> bool:
        """Authenticate with the PhenoML API"""
        auth_data = {"identity": self.email, "password": self.password}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/collections/users/auth-with-password?fields=token",
                json=auth_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                self.token = response.json().get('token')
                print("✓ Authentication successful!")
                return True
            else:
                print(f"✗ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Authentication error: {str(e)}")
            return False
    
    def request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to API"""
        if not self.token:
            print("✗ No authentication token available")
            return None
            
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response.json()
            
        except Exception as e:
            print(f"✗ Request error: {str(e)}")
            return None


def demo_lang2fhir_create(client: PhenoMLClient, resource_type: str, text: str, provider: str = None, fhir_store_id: str = None, on_behalf_of_email: str = None):
    """Create FHIR resources from natural language"""
    print(f"\n Creating {resource_type} from: '{text}'")
    
    data = {"resource": resource_type, "text": text}
    if provider:
        data["provider"] = provider
    
    # Build meta object if we have any meta parameters
    meta = {}
    if fhir_store_id:
        meta["fhir_store_id"] = fhir_store_id
    if on_behalf_of_email:
        meta["on_behalf_of_email"] = on_behalf_of_email
    
    if meta:
        data["meta"] = meta
    
    # Debug: Print the exact request payload
    print(f" Request payload: {json.dumps(data, indent=2)}")
        
    response = client.request('POST', '/tools/lang2fhir-and-create', data)
    
    if response and response.get('success'):
        print("✓ Resource created successfully!")
        fhir_resource = response.get('fhir_resource', {})
        print(f"  Type: {fhir_resource.get('resourceType')}")
        print(f"  ID: {response.get('fhir_id')}")
        if response.get('message'):
            print(f"  Message: {response.get('message')}")
        return response
    else:
        print("✗ Failed to create resource")
        if response:
            print(f"  Error: {response.get('message', 'Unknown error')}")
        return None


def demo_lang2fhir_search(client: PhenoMLClient, text: str, provider: str = None, fhir_store_id: str = None, on_behalf_of_email: str = None, patient_id: str = None, practitioner_id: str = None, count: int = None):
    """Search FHIR resources using natural language"""
    print(f"\n Searching for: '{text}'")
    
    data = {"text": text}
    if provider:
        data["provider"] = provider
    
    # Build meta object if we have any meta parameters
    meta = {}
    if fhir_store_id:
        meta["fhir_store_id"] = fhir_store_id
    if on_behalf_of_email:
        meta["on_behalf_of_email"] = on_behalf_of_email
    
    if meta:
        data["meta"] = meta
        
    if patient_id:
        data["patient_id"] = patient_id
    if practitioner_id:
        data["practitioner_id"] = practitioner_id
    if count:
        data["count"] = count
    
    # Debug: Print the exact request payload
    print(f"Request payload: {json.dumps(data, indent=2)}")
    
    response = client.request('POST', '/tools/lang2fhir-and-search', data)
    
    if response and response.get('success'):
        results = response.get('fhir_results', [])
        resource_type = response.get('resource_type', 'Unknown')
        search_params = response.get('search_params', '')
        
        print(f"✓ Found {len(results)} results")
        print(f"  Resource Type: {resource_type}")
        print(f"  Search Params: {search_params}")
        
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. {result.get('resourceType')} (ID: {result.get('id')})")
            
        if len(results) > 3:
            print(f"  ... and {len(results) - 3} more")
            
        if response.get('message'):
            print(f"  Message: {response.get('message')}")
        return response
    else:
        print("✗ Search failed")
        if response:
            print(f"  Error: {response.get('message', 'Unknown error')}")
        return None


def create_prompt(client: PhenoMLClient, name: str, content: str, description: str = None) -> Optional[str]:
    """Create an AI agent prompt"""
    print(f"\n Creating prompt: '{name}'")
    
    data = {
        "name": name,
        "description": description or f"Prompt for {name}",
        "type": "system",
        "content": content,
        "is_active": True,
        "is_default": False,
        "tags": ["demo"]
    }
    
    response = client.request('POST', '/agent/prompts', data)
    
    if response and response.get('success'):
        prompt_id = response.get('data', {}).get('id') or response.get('id')
        if prompt_id:
            print(f"✓ Prompt created with ID: {prompt_id}")
            return prompt_id
    
    # Try to find existing prompt
    response = client.request('GET', '/agent/prompts')
    if response and response.get('success'):
        prompts = response.get('prompts', []) or response.get('data', [])
        for prompt in prompts:
            if prompt.get('name') == name:
                prompt_id = prompt.get('id')
                print(f"✓ Found existing prompt with ID: {prompt_id}")
                return prompt_id
    
    print("✗ Failed to create or find prompt")
    return None


def create_agent(client: PhenoMLClient, name: str, prompts: List[str], tools: List[str] = None, provider: str = None, meta: Dict = None) -> Optional[str]:
    """Create an AI agent"""
    print(f"\n Creating agent: '{name}'")
    
    data = {
        "name": name,
        "description": f"AI agent for {name}",
        "prompts": prompts,  # Array of prompt IDs
        "is_active": True,
        "tools": tools or ["lang2fhir_create", "lang2fhir_search"],
        "tags": ["demo"]
    }
    
    if provider:
        data["provider"] = provider
    
    if meta:
        data["meta"] = meta
    
    response = client.request('POST', '/agent/create', data)
    
    if response and response.get('success'):
        agent_id = response.get('data', {}).get('id')
        if agent_id:
            print(f"✓ Agent created with ID: {agent_id}")
            return agent_id
    
    print("✗ Failed to create agent")
    return None


def chat_with_agent(client: PhenoMLClient, message: str, agent_id: str, session_id: str = None):
    """Chat with a specific agent"""
    print(f"\n Chatting with agent: '{message}'")
    
    data = {"message": message, "agent_id": agent_id, "session_id": session_id}
    response = client.request('POST', '/agent/chat', data)
    
    if response and response.get('success'):
        print(f" Agent: {response.get('response', 'No response')}")
        return response
    else:
        print("✗ Chat failed")
        if response:
            print(f"  Error: {response.get('message', 'Unknown error')}")
        return None


def list_prompts(client: PhenoMLClient):
    """List all available prompts"""
    print("\n Listing prompts...")
    
    response = client.request('GET', '/agent/prompts')
    
    if response and response.get('success'):
        prompts = response.get('prompts', []) or response.get('data', [])
        print(f"✓ Found {len(prompts)} prompts")
        
        for i, prompt in enumerate(prompts):
            print(f"  {i+1}. {prompt.get('name')} (ID: {prompt.get('id')})")
            print(f"     Description: {prompt.get('description', 'No description')}")
            print(f"     Active: {prompt.get('is_active')}")
            print()
        
        return prompts
    else:
        print("✗ Failed to list prompts")
        return None


def list_agents(client: PhenoMLClient):
    """List all available agents"""
    print("\n Listing agents...")
    
    response = client.request('GET', '/agent/list')
    
    if response and response.get('success'):
        agents = response.get('agents', []) or response.get('data', [])
        print(f"✓ Found {len(agents)} agents")
        
        for i, agent in enumerate(agents):
            print(f"  {i+1}. {agent.get('name')} (ID: {agent.get('id')})")
            print(f"     Description: {agent.get('description', 'No description')}")
            print(f"     Tools: {agent.get('tools', [])}")
            print(f"     Active: {agent.get('is_active')}")
            print()
        
        return agents
    else:
        print("✗ Failed to list agents")
        return None


def extract_medical_codes(client: PhenoMLClient, 
                         text: str, 
                         system_name: str = "ICD-10-CM", 
                         system_version: str = "2025",
                         chunking_method: str = "none",
                         max_codes_per_chunk: int = 20,
                         code_similarity_filter: float = 0.9,
                         include_rationale: bool = True):
    """Extract medical codes from natural language text using construe extract"""
    print(f"\n Extracting medical codes from: '{text}'")
    
    data = {
        "system": {
            "name": system_name,
            "version": system_version
        },
        "config": {
            "chunking_method": chunking_method,
            "max_codes_per_chunk": max_codes_per_chunk,
            "code_similarity_filter": code_similarity_filter,
            "include_rationale": include_rationale
        },
        "text": text
    }
    
    # Debug: Print the exact request payload
    print(f" Request payload: {json.dumps(data, indent=2)}")
        
    response = client.request('POST', '/construe/extract', data)
    
    if response:
        # Check if response has codes directly (successful response)
        if response.get('codes'):
            print("✓ Medical codes extracted successfully!")
            
            codes = response.get('codes', [])
            system_info = response.get('system', {})
            system_name = system_info.get('name', 'Unknown')
            system_version = system_info.get('version', 'Unknown')
            
            print(f"   System: {system_name} {system_version}")
            print(f"   Found {len(codes)} medical codes:")
            
            for i, code in enumerate(codes):
                code_value = code.get('code', 'Unknown')
                description = code.get('description', 'No description')
                reason = code.get('reason', '')
                
                print(f"    {i+1}. Code: {code_value}")
                print(f"       Description: {description}")
                if reason and include_rationale:
                    print(f"       Reason: {reason}")
                print()
            
            return response
        else:
            print("✗ Failed to extract medical codes")
            if response.get('message'):
                print(f"   Error: {response.get('message')}")
            elif response.get('error'):
                print(f"   Error: {response.get('error')}")
            else:
                print("   Error: Unknown error occurred")
            return None
    else:
        print("✗ Failed to extract medical codes")
        print("   Error: No response received")
        return None 