from typing import Any, Dict, List, Optional
from google.auth.transport import requests
from google.cloud import firestore
import google.oauth2.id_token
from fastapi import Request
from fastapi import HTTPException
from datetime import date, datetime, time

from pydantic_models.models import Task, User, Workspace, WorkspaceSummary

firestore_db = firestore.Client()

firebase_request_adapter = requests.Request()

class Service:


    @staticmethod
    def get_task(workspace_id:str,task_id:str,user:User):
        try:
            workspace = Service.get_workspace(user,workspace_id)
            if user['email'] not in workspace['board']['users'] and workspace['board']['created_by']!=user['email']:
                raise Exception("you are not allowed to view this")
            doc_ref = firestore_db.collection('tasks').document(task_id)
            task = doc_ref.get()
            if not task.exists:
                raise Exception("Invalid task id")
            task_data = task.to_dict()
            task_data["id"] = task_id
            
            if task_data.get("due_date"):
                if isinstance(task_data["due_date"], date):
                    task_data["due_date"] = task_data["due_date"].strftime('%Y-%m-%d')
                    
            if task_data.get("due_time"):
                if isinstance(task_data["due_time"], time):
                    task_data["due_time"] = task_data["due_time"].strftime('%H:%M')
                    
            if task_data.get("completed_at"):
                if isinstance(task_data["completed_at"], datetime):
                    task_data["completed_at"] = task_data["completed_at"].strftime('%b %d, %Y at %I:%M %p')
            if task_data.get("created_at"):
                if isinstance(task_data["created_at"], datetime):
                    task_data["created_at"] = task_data["created_at"].strftime('%Y-%m-%d %H:%M:%S')
            return task_data
        except Exception as e:
            print(e)
            raise Exception(e)
        
    @staticmethod
    def delete_workspace(workspace_id:str,user:User):
        try:
            doc_ref = firestore_db.collection('workspaces').document(workspace_id)
            snapshot = doc_ref.get()

            if not snapshot.exists:
                raise Exception("Workspace does not exist")

            workspace_data = snapshot.to_dict()

            if workspace_data.get("created_by") != user['email']:
                raise Exception("Only the creator of the workspace can delete the board")

            if len(workspace_data.get("users"))>=1:
                raise Exception("Remove all users from the workspace before deleting it")

            doc_ref.delete()
            return {"message": "Taskboard deleted successfully", "id": workspace_id}
        except Exception as e:
            raise Exception(str(e))

    @staticmethod
    def delete_task(workspace_id:str,task_id:str,user:User):
        try:
            workspace = Service.get_workspace(user,workspace_id)

            if not workspace or 'board' not in workspace:
                raise Exception("Invalid workspace or missing board data")
            if user['email'] not in workspace['board']['users'] and workspace['board']['created_by'] != user['email']:
                raise Exception("You are not allowed to do this")

            doc_ref = firestore_db.collection('tasks').document(task_id)
            task = doc_ref.get()
            if not task.exists:
                raise Exception("Invalid task id")
            doc_ref.delete() 
        except Exception as e:
            print(e)
            raise Exception(str(e))
        
    @staticmethod
    def mark_task_as_complete(workspace_id:str,task_id: str,user:User):
        try:

            doc_ref = firestore_db.collection('workspaces').document(workspace_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise Exception("Invalid workspace Id")

            data = doc.to_dict()
            created_by = data.get("created_by")
            users = data.get("users", [])

            if user['email'] != created_by and user['email'] not in users:
                raise Exception("you are not allowed to do this")

            doc_ref = firestore_db.collection('tasks').document(task_id)
            task = doc_ref.get()
            if not task.exists:
                raise Exception("Invalid task id")
            current_datetime = datetime.now()
            doc_ref.update({
                "status": "completed",
                "due_date": current_datetime.date().isoformat(), 
                "due_time": current_datetime.time().strftime("%H:%M:%S")  
            })
        except Exception as e:
            print(e)
            raise Exception(str(e))

    @staticmethod
    def remove_user_in_tasks(workspace_id,users):
        try:
            wokrspace_ref = firestore_db.collection("tasks")
            matching_tasks = wokrspace_ref.where("workspace_id", "==", workspace_id).get()

            for task_doc in matching_tasks:
                task_data = task_doc.to_dict()
                current_assignees = task_data.get("assigned_to", [])

                valid_assignees = [email for email in current_assignees if email in users]

                if set(current_assignees) != set(valid_assignees):
                    wokrspace_ref.document(task_doc.id).update({
                        "assigned_to": valid_assignees
                    })

        except Exception as e:
            raise Exception(f"Error while updating task assignees for workspace '{workspace_id}': {str(e)}")

    @staticmethod
    def create_task(workspace_id:str,task:Task,user:User):
        try:
            workspace = Service.get_workspace(user,workspace_id)
            if workspace["board"]["created_by"] != user["email"] and user.email not in workspace['board']['users']:
                raise PermissionError("Only the memebers can add tasks to this workspace.")
            existing_task = (
                firestore_db.collection('tasks')
                .where(filter=firestore.FieldFilter("board_id", "==", task.workspace_id))
                .where(filter=firestore.FieldFilter("title", "==", task.title))
                .limit(1)
                .get()
            )

            if len(existing_task) > 0:
                raise Exception("Tasks in the same workspace must have different names")
            task_dict = task.dict(exclude_none=True)
            if task.due_date:
                task_dict['due_date'] = task.due_date.isoformat()
            if task.due_time:
                task_dict['due_time'] = task.due_time.strftime("%H:%M")

            firestore_db.collection("tasks").add(task_dict)
            print(task_dict)
        except Exception as e:
            print(f"Firestore error: {e}")  
            raise Exception(str(e))

    @staticmethod
    def update_task(workspace_id:str,task_id:str,task:Task,user:User):
        try:
            workspace = Service.get_workspace(user,workspace_id)
            print(user)
            if workspace["board"]["created_by"] != user["email"] and user['email'] not in workspace['board']['users']:
                raise PermissionError("Only the memebers can add/update tasks to this workspace.")
            print(task.workspace_id)
            print(workspa)
            if task.workspace_id != workspace_id:
                raise Exception("Task does not belongs to given workspace id")
            task_ref = firestore_db.collection("tasks").document(task_id)
            snapshot = task_ref.get()
            task_dict = task.dict(exclude_none=True)
            if not snapshot.exists:
                raise Exception("Invalid task id please enter valid task id")
            if task.due_date:
                task_dict['due_date'] = task.due_date.isoformat()
            if task.due_time:
                task_dict['due_time'] = task.due_time.strftime("%H:%M")  
            task_ref.update(task_dict)
            print(task_dict)
        except Exception as e:
            print(e)
            raise Exception(str(e))

    @staticmethod
    def check_login_and_return_user(request):
        token = request.cookies.get("token")
        if not token:
            return None

        try:
            user_token = google.oauth2.id_token.verify_firebase_token(token, firebase_request_adapter)
            if not user_token:
                return None

            email = user_token.get("email")
            if not email:
                return None
            user = {
                "email": email,
                "name": email.split("@")[0]
            }

            return user
        except Exception:
            return None

    @staticmethod
    def create_user_into_firestore(request:Request):
        token = request.cookies.get("token")
        if not token:
            return None
        try:
            user_token = google.oauth2.id_token.verify_firebase_token(token, firebase_request_adapter)
            if not user_token:
                return None

            email = user_token.get("email")
            if not email:
                return None

            name = email.split("@")[0]
            users_ref = firestore_db.collection("users")
            existing_users = users_ref.where("email", "==", email).limit(1).stream()

            if not any(existing_users):
                users_ref.add({"email": email, "name": name})

            return {"email": email, "name": name}
        except Exception:
            return None
        
    @staticmethod
    def get_workspaces_of_user(user:User)->List["WorkspaceSummary"]:
        try:
            summaries = []
            seen_ids = set()

            member_query = firestore_db.collection("workspaces").where("users", "array_contains", user['email']).stream()
            creator_query = firestore_db.collection("workspaces").where("created_by", "==", user['email']).stream()


            for doc in list(member_query) + list(creator_query):
                if doc.id in seen_ids:
                    continue
                seen_ids.add(doc.id)

                workspace_id = doc.id
                data = doc.to_dict()
                users = data.get("users", [])
                created_by = data.get("created_by", "")
                title = data.get("title", "")

                tasks = firestore_db.collection("tasks").where("workspace_id", "==", workspace_id).stream()

                total_tasks = 0
                completed_tasks = 0
                last_activity = None

                for task_doc in tasks:
                    task = task_doc.to_dict()
                    total_tasks += 1
                    if task.get("status") == "completed":
                        completed_tasks += 1
                    updated_at = task.get("updated_at")
                    if updated_at and (not last_activity or updated_at > last_activity):
                        last_activity = updated_at

                summaries.append(WorkspaceSummary(
                    id=workspace_id,
                    title=title,
                    created_by=created_by,
                    users=users,
                    total_mem=len(users),
                    total_tasks=total_tasks,
                    completed_tasks=completed_tasks,
                    active_tasks=total_tasks - completed_tasks,
                    last_activity=last_activity
                ))

            return summaries
        except Exception as e:
            print(f"[WorkspaceSummary Error] {e}")
            return []
        
    
    @staticmethod
    def get_all_users() -> List[User]:

        users =  [doc.to_dict() for doc in firestore_db.collection("users").stream()]
        print("inside users of get all users ",users)
        return users
    
    @staticmethod
    def create_workspace(workspace:Workspace,user:User):
        try:
            if firestore_db.collection("workspaces").where("title", "==", workspace.title).limit(1).get():
                raise HTTPException(status_code=400, detail="Workspace name already exists. Please choose a different name.")
            existing_users_docs = firestore_db.collection("users").stream()
            existing_emails = {doc.to_dict().get("email") for doc in existing_users_docs}
            invalid_users = [u for u in workspace.users if u not in existing_emails]
            if invalid_users:
                raise HTTPException(
                    status_code=400,
                    detail=f"These users were not found in the system: {', '.join(invalid_users)}"
                )
            firestore_db.collection("workspaces").add(workspace.dict())
        except Exception as e:
            raise Exception(str(e))
            
    @staticmethod
    def get_workspace(user:User,workspace_id:str)->Optional[Dict]:
        try:
            workspace_snapshot = firestore_db.collection("workspaces").document(workspace_id).get()
            if not workspace_snapshot.exists:
                raise ValueError(f"Task board with ID '{workspace_id}' does not exist.")
            workspace_data = workspace_snapshot.to_dict()
            workspace_data["id"] = workspace_snapshot.id
            users = Service.get_all_users()
            board = workspace_data
            response = {
                'users':users,
                'current_user':user,
                'board':board,
                'tasks':Service.get_tasks(workspace_id)
            }
            return response
        except Exception as e:
            raise Exception(str(e))
        
    @staticmethod
    def update_workspace(request:Request,workspace_id:str,user:User,workspace:Workspace):
        try:
            workspace_ref = firestore_db.collection("workspaces").document(workspace_id)
            workspace_snap = workspace_ref.get()
            if not workspace_snap.exists:
                raise ValueError(f"Work Space with ID '{workspace_id}' does not exist.")
            existing_data = workspace_snap.to_dict()
            if user['email'] != existing_data.get("created_by"):
                raise PermissionError("Only the creator can update the task board.")
            conflicting_workspaces = (
                firestore_db.collection("workspaces")
                .where("title", "==", workspace.title)
                .get()
            )
            for board in conflicting_workspaces:
                if board.id != workspace_id:
                    raise ValueError(f"A task board with title '{workspace.title}' already exists.")
            for user_email in workspace.users:
                user_query = (
                    firestore_db.collection("users")
                    .where("email", "==", user_email)
                    .limit(1)
                    .get()
                )
                if not user_query:
                    raise ValueError(f"User '{user_email}' does not exist. Only registered users can be added.")
            workspace_ref.update({
            "title": workspace.title,
            "users": workspace.users,
            })
            Service.remove_user_in_tasks(workspace_id,workspace.users)
            response = {
                "id": workspace_id,
                 "title": workspace.title,
                 "users": workspace.users,
                 "created_by": workspace.created_by,
                 'tasks':Service.get_tasks(workspace_id)
            }
            print(len(workspace.users))
            
            return response

        except Exception as e:
            print(e)
            raise Exception(str(e))
        
    @staticmethod
    def get_tasks(workspace_id: str) -> List[Dict[str, Any]]:
        try:

            tasks_ref = firestore_db.collection('tasks')
            tasks_query = tasks_ref.where('workspace_id', '==', workspace_id).stream()
            task_list = []

            for task_doc in tasks_query:
                task_data = task_doc.to_dict()

                task_data['id'] = task_doc.id

                
                due_date = task_data.get('due_date')
                if due_date:
                    task_data['due_date'] = Service._parse_date(due_date)

                
                due_time = task_data.get('due_time')
                if due_time:
                    task_data['due_time'] = Service._parse_time(due_time)

               
                assigned_to = task_data.get('assigned_to') or []
                task_data['unassigned'] = not assigned_to

                task_list.append(task_data)

            return task_list

        except Exception as e:
            raise Exception(f"Error getting tasks: {e}")

    @staticmethod
    def _parse_date(value) -> Any:
       
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None
        elif isinstance(value, datetime):
            return value.date()
        return None

    @staticmethod
    def _parse_time(value) -> Any:
       
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%H:%M:%S").time()
            except ValueError:
                return None
        elif isinstance(value, datetime):
            return value.time()
        return None
    