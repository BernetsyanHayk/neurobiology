"""
This file contains async functions to execute DB query and retrieve the data, handling SQLAlchemy errors.
"""
import logging
import sys
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

#############################################
# Function to execute a query and return the first column value
#############################################
async def execute_query(session, *args, skip_commit=False, migration=False):
    try:
        async with session as async_session:
            result = await async_session.execute(*args)
            if not skip_commit:
                await async_session.commit()

            # Check if the result has rows to fetch
            if result.returns_rows:
                record = result.fetchone()
                if record:
                    # Return the first column value if a record was found
                    return record[0]
                else:
                    return None
            else:
                return "no_data_in_result"

    except SQLAlchemyError as e:
        if not migration:
            logging.error(f"Error executing query: \n Query: {args[0].text} \n Error: {e}")
            return f"Error executing query {args[0].text}: {e}"
        else:
            logging.error(f"Error executing migration: \n Error: {e}")
            return f"Error executing migration: {e}"
    except Exception as e:
        # Handle other exceptions
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_line = exc_traceback.tb_lineno
        return f"Error executing query: An exception of type {type(e).__name__} occurred on line {error_line}: {str(e)}"

#############################################
# Function to return error in JSON structure with actual message and status code
#############################################
def db_error(message, code):
    return JSONResponse(content={"message": message}, status_code=code)
