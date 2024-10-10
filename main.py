from typing import Optional
from fastapi import FastAPI, HTTPException, Request,Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore
from pydantic_models.models import Task, Workspace
from services.service import Service
import google.oauth2.id_token
from fastapi.responses import RedirectResponse

app = FastAPI()



app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    create_user_into_firestore(request)
    return templates.TemplateResponse(
        "home.html",
        {"request": request}
    )

def create_user_into_firestore(request:Request):
    try:
        return Service.create_user_into_firestore(request)
    except Exception as e:
        raise Exception(str(e))
    
def check_login_and_return_user(request:Request):
    try:
        user = Service.check_login_and_return_user(request)
        return user
    except Exception as e:
        raise Exception (str(e))
    

@app.get("/workspaces",response_class=RedirectResponse)
def get_workspaces_of_user(request:Request):
    try:
        user = check_login_and_return_user(request)
        if not user:
            return RedirectResponse(url="/")
        workspaces = Service.get_workspaces_of_user(user)
        return templates.TemplateResponse(
            "workspaces.html",
            {"request":request,"workspaces":workspaces,"user":user}
        )
    except Exception as e:
        print(e)
        return RedirectResponse(
            url=f"/workspaces?error={str(e)}",
            status_code=303
        )

@app.get("/workspaces/create",response_class=HTMLResponse)
def create_workspaces(request:Request):
    try:
        print("hello")
        user = check_login_and_return_user(request)
        print(user)
        print("hello")
        if user :
            print('call here ')
            users = Service.get_all_users()
            print('inside users ',users)
            return templates.TemplateResponse(
            "create_workspace.html",
                {
                    "request": request,
                    "users": users,
                    "current_user": user,
                    "board": None
                }
            )
        else:
            print("not logged in")
            return RedirectResponse(url="/", status_code=302)
    except Exception as e:
        print(e)
        return RedirectResponse(url="/")
    
@app.post("/workspaces/create",response_class=RedirectResponse)
def create_workspace(request:Request,workspace: Workspace = Depends(Workspace.from_form)):
    user = Service.check_login_and_return_user(request)
    try:
        if user:
            Service.create_workspace(workspace,user)
        else :
            return RedirectResponse(url="/",status_code=303)
        return RedirectResponse(
            url="/workspaces",
            status_code=303
        )
    except Exception as e:
        return templates.TemplateResponse(
           "create_workspace.html", 
            {"request": request,
             "users":Service.get_all_users(),
             "current_user":user,
             "board": None,
             "error":str(e)
            })
    
@app.get("/workspaces/{workspace_id}")
def get_workspace(request:Request,workspace_id:str,error: Optional[str] = None):
    user = Service.check_login_and_return_user(request)
    try:
        result = Service.get_workspace(user,workspace_id)
        print("result ", result['board']['users'])
        return templates.TemplateResponse("create_workspace.html", {
            "request": request,
            "users": result['board']['users'],
            "current_user": result['current_user'],
            "board": result['board'],
            "tasks": result['tasks'],
            "error": error 
        })
    except Exception as e:
        pass

@app.post("/workspaces/{workspace_id}")
def update_workspace(request: Request, workspace_id: str, workspace: Workspace = Depends(Workspace.from_form)):
    print("but wby")
    user = Service.check_login_and_return_user(request)
    try:
       result = Service.update_workspace(request,workspace_id,user,workspace)
       return templates.TemplateResponse("create_workspace.html", {
            "request": request,
            "users": Service.get_all_users(),
            "current_user": user,
            "board": result,
            "tasks": result['tasks']
        })
    except Exception as e:
        task_board = Service.get_workspace(user,workspace_id,)
        tasks =[]
        return templates.TemplateResponse("create_workspace.html", {
            "request": request,
            "users": Service.get_all_users(),
            "current_user": user,
            "board": task_board,
            "tasks": tasks,
            "error": str(e) 
        })
    
@app.post("/workspaces/{workspace_id}/tasks",response_class=RedirectResponse)
def create_task(request:Request,workspace_id:str,task:Task=Depends(Task.from_form)):
    print("no hit")
    user=check_login_and_return_user(request)
    try:
        if user:
            task.workspace_id = workspace_id
            Service.create_task(workspace_id,task,user)
            return RedirectResponse(
            url=f"/workspaces/{workspace_id}",
            status_code=303
        )
        else :
            return RedirectResponse(url="/",status_code=303)
    except Exception as e:
        return RedirectResponse(
            url=f"/workspaces/{workspace_id}?error={str(e)}",
            status_code=303
        )

@app.post('/workspaces/{workspace_id}/tasks/{task_id}',response_class=RedirectResponse)
def update_task(request:Request,workspace_id,task_id,task:Task=Depends(Task.from_form)):
    user = check_login_and_return_user(request)
    try:
        if user:
            Service.update_task(workspace_id,task_id,task,user)
            return RedirectResponse(
            url=f"/workspaces/{workspace_id}",
            status_code=303
        )
        else:
            return RedirectResponse(url="/",status_code=303)
    except Exception as e:
       print(e)
       return RedirectResponse(
            url=f"/workspaces/{workspace_id}?error={str(e)}",
            status_code=303
        )
    
@app.delete("/workspaces/{workspace_id}/tasks/{task_id}")
def delete_task(request:Request,workspace_id:str,task_id:str):
    user = check_login_and_return_user(request)
    try:
        Service.delete_task(workspace_id,task_id,user)
        return JSONResponse(status_code=200, content={"message": "Task deleted successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/workspaces/{workspace_id}/tasks/{task_id}/mark-complete")
def mark_task_completion(request: Request, workspace_id:str,task_id: str):
    user = check_login_and_return_user(request)
    try:
        Service.mark_task_as_complete(workspace_id,task_id,user)
        return JSONResponse(status_code=200, content={"message": "Task marked as completed successfully"})
    except Exception as e:
        print(e)
        return JSONResponse(status_code=500, content={"error": str(e)})
    

@app.post("/workspaces/{workspace_id}/delete",response_class=RedirectResponse)
def delete_taskboard(request:Request,workspace_id:str):
    user = check_login_and_return_user(request)
    try:
        if user:
            Service.delete_workspace(workspace_id,user)
            return RedirectResponse(
            url=f"/workspaces",
            status_code=303
        )
    except Exception as e:
        print("Error while deleting:", str(e))
        return RedirectResponse(
            url=f"/workspaces/{workspace_id}/?error={str(e)}",
            status_code=303
        )
    

@app.get('/workspaces/{workspace_id}/tasks/{task_id}')
def get_task(request:Request,workspace_id:str,task_id:str):
    user = check_login_and_return_user(request)
    try:
        task = Service.get_task(workspace_id,task_id,user)
        print('recieved task')
        print(task)
        if not task:
            return JSONResponse(status_code=404, content={"error": "Task not found"})
        return JSONResponse(status_code=200, content=task)
    except Exception as e:
        print(e)
        return JSONResponse(status_code=500, content={"error": str(e)})