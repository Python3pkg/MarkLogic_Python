#
# Copyright 2015 MarkLogic Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# File History
# ------------
#
# Paul Hoehne       03/26/2015     Initial development
#


class MLClientException(Exception):
    """
    Base class for MarkLogic client exceptions.

    """
    pass


class UnexpectedManagementAPIResponse(MLClientException):
    """
    This exception class is for exceptions that arise from unexpected management
    API responses.

    """
    pass


class UnexpectedAPIResponse(MLClientException):
    """
    This exception class is for exceptions that arise from unexpected REST api
    responses when dealing with search or documents.

    """
    pass

class InvalidValue(MLClientException):
    """
    This exception class is for exceptions that arise from attempts to
    set properties to invalid values, passing a dictionary where a list
    is expected, for example.

    """
    pass
