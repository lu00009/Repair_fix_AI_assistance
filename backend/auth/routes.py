from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from backend.supabase_client import supabase

router = APIRouter()

# -------------------- Models --------------------
class UserSignUp(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# -------------------- Helper --------------------
def verify_token(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# -------------------- Routes --------------------
@router.post("/signup")
def signup(user: UserSignUp):
    response = supabase.auth.sign_up({
        "email": user.email,
        "password": user.password
    })
    return response

@router.post("/login")
def login(user: UserLogin):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        
        # Return formatted response with access token
        if response.session:
            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
                },
                "message": "Login successful"
            }
        else:
            raise HTTPException(status_code=401, detail="Login failed")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")

@router.get("/me")
def me(user=Depends(verify_token)):
    return user

@router.post("/logout")
def logout(user=Depends(verify_token)):
    supabase.auth.sign_out(user['access_token'])
    return {"message": "Logged out successfully"}
