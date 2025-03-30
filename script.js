$(document).ready(function() {
    // Main task loading and management functions
    loadTasks();
  
    function loadTasks() {
      $.ajax({
        url: '/tasks',
        type: 'GET',
        success: function(tasks) {
          const taskList = $('#tasksContainer');
          taskList.empty();
  
          if (Object.keys(tasks).length === 0) {
            taskList.html('<div class="ui message">No tasks found. Add some tasks to get started!</div>');
            return;
          }
  
          let listHtml = '<div class="ui relaxed divided list">';
          $.each(tasks, function(taskId, task) {
            const isCompleted = task.status === "Completed";
            listHtml += `
              <div class="item task-item ${isCompleted ? 'completed' : ''}">
                <div class="content">
                  <div class="header">${task.title}</div>
                  <div class="description">${task.desc || 'No description'}</div>
                  <div class="meta">
                    <span class="category">${task.category}</span> | 
                    <span class="priority">${task.priority}</span> | 
                    <span class="due-date">Due: ${task.due_date || 'No due date'}</span>
                  </div>
                  <div class="right floated">
                    <button class="ui red mini button" onclick="deleteTask('${taskId}')">Delete</button>
                    <button id="completeBtn-${taskId}" class="ui blue mini button" 
                      onclick="completeTask('${taskId}')" ${isCompleted ? 'disabled' : ''}>
                      ${isCompleted ? 'Completed' : 'Complete'}
                    </button>
                    <button class="ui green mini button" onclick="updateTask('${taskId}')">Update</button>
                    <button class="ui teal mini button" onclick="enhanceDescription('${taskId}')">Enhance</button>
                    <button class="ui yellow mini button" onclick="aiPrioritize('${taskId}')">AI Priority</button>
                  </div>
                </div>
              </div>
            `;
          });
          listHtml += '</div>';
          taskList.html(listHtml);
        },
        error: function(err) {
          alert("Error loading tasks: " + (err.responseJSON?.error || "Unknown error"));
        }
      });
    }
  
    // Add new task via POST /tasks
    $('#addTaskForm').submit(function(e) {
      e.preventDefault();
      const title = $('#taskTitle').val();
      const desc = $('#taskDesc').val();
      const priority = $('#taskPriority').val();
      const due_date = $('#taskDueDate').val();
      const category = $('#taskCategory').val();
  
      if (!title) {
        alert("Task title is required!");
        return;
      }
      if (due_date && !validateDueDate(due_date)) {
        return;
      }
      
      $.ajax({
        url: '/tasks',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ title, desc, priority, due_date, category, status: "Pending" }),
        success: function() {
          loadTasks();
          $('#addTaskForm')[0].reset();
          $('#taskPriority').val("Low");
          $('#taskCategory').val("Work");
        },
        error: function(err) {
          alert("Error: " + (err.responseJSON?.error || "Unknown error"));
        }
      });
    });
  
    function validateDueDate(dueDate) {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const dueDateObj = new Date(dueDate);
      if (dueDateObj < today) {
        alert("Due date cannot be in the past!");
        return false;
      }
      return true;
    }
  
    // Task operation functions (complete, delete, update, etc.)
    window.completeTask = function(taskId) {
      $.ajax({
        url: `/tasks/${taskId}`,
        type: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify({ status: "Completed" }),
        success: function() { loadTasks(); },
        error: function(err) {
          alert("Error: " + (err.responseJSON?.error || "Unknown error"));
        }
      });
    };
  
    window.deleteTask = function(taskId) {
      if (confirm("Are you sure you want to delete this task?")) {
        $.ajax({
          url: `/tasks/${taskId}`,
          type: 'DELETE',
          success: function() { loadTasks(); },
          error: function(err) {
            alert("Error: " + (err.responseJSON?.error || "Unknown error"));
          }
        });
      }
    };
  
    window.updateTask = function(taskId) {
      let newTitle = prompt("Enter new title (leave empty to keep current):");
      let newDesc = prompt("Enter new description (leave empty to keep current):");
      let newPriority = prompt("Enter new priority (Low, Medium, High, Urgent) (leave empty to keep current):");
      let newDueDate = prompt("Enter new due date (YYYY-MM-DD) (leave empty to keep current):");
      let newCategory = prompt("Enter new category (leave empty to keep current):");
  
      let updates = {};
      if (newTitle) updates.title = newTitle;
      if (newDesc) updates.desc = newDesc;
      if (newPriority) updates.priority = newPriority;
      if (newDueDate) updates.due_date = newDueDate;
      if (newCategory) updates.category = newCategory;
  
      if (Object.keys(updates).length > 0) {
        $.ajax({
          url: `/tasks/${taskId}`,
          type: 'PUT',
          contentType: 'application/json',
          data: JSON.stringify(updates),
          success: function() { loadTasks(); },
          error: function(err) {
            alert("Error: " + (err.responseJSON?.error || "Unknown error"));
          }
        });
      }
    };
  
    // AI Task query handler (main content)
    $('#aiTaskBtn').click(function() {
      let query = $('#aiTaskQuery').val().trim();
      if (!query) {
        alert("Please enter a query.");
        return;
      }
      $('#aiTaskResult').html('<div class="ui active inline loader"></div> Thinking...').removeClass('hidden');
      $.ajax({
        url: '/ai-task',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ query: query }),
        success: function(res) {
          $('#aiTaskResult').html("<strong>AI Response:</strong> " + res.ai_response);
        },
        error: function(err) {
          $('#aiTaskResult').html("Error: " + (err.responseJSON?.error || "Request failed"));
          alert("Error: " + (err.responseJSON?.error || "Unknown error"));
        }
      });
    });
  
    // AI Task Summarization
    $('#aiSummarizeBtn').click(function() {
      $('#aiTaskResult').html('<div class="ui active inline loader"></div> Generating summary...').removeClass('hidden');
      $.ajax({
        url: '/ai-summarize',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({}),
        success: function(res) {
          $('#aiTaskResult').html("<strong>Task Summary:</strong><br>" + res.summary.replace(/\n/g, '<br>'));
        },
        error: function(err) {
          $('#aiTaskResult').html("Error: " + (err.responseJSON?.error || "Request failed"));
        }
      });
    });
  
    // AI Task Search
    $('#aiSearchBtn').click(function() {
      let query = prompt("What would you like to search for in your tasks?");
      if (!query) return;
      $('#aiTaskResult').html('<div class="ui active inline loader"></div> Searching...').removeClass('hidden');
      $.ajax({
        url: '/ai-search',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ query: query }),
        success: function(res) {
          if (Object.keys(res.results).length === 0) {
            $('#aiTaskResult').html("<strong>Search Results:</strong> No matching tasks found.");
            return;
          }
          let resultHtml = "<strong>Search Results:</strong><br><div class='ui list'>";
          $.each(res.results, function(id, task) {
            resultHtml += `<div class="item">
                <i class="right triangle icon"></i>
                <div class="content">
                  <div class="header">${task.title}</div>
                  <div class="description">${task.desc || 'No description'}</div>
                </div>
              </div>`;
          });
          resultHtml += "</div>";
          $('#aiTaskResult').html(resultHtml);
        },
        error: function(err) {
          $('#aiTaskResult').html("Error: " + (err.responseJSON?.error || "Request failed"));
        }
      });
    });
  
    // AI Enhance Description
    window.enhanceDescription = function(taskId) {
      $('#aiTaskResult').html('<div class="ui active inline loader"></div> Enhancing description...').removeClass('hidden');
      $.ajax({
        url: '/ai-enhance-description',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ task_id: taskId }),
        success: function(res) {
          $('#aiTaskResult').html("<strong>Description Enhanced:</strong> Task description has been improved.");
          loadTasks();
        },
        error: function(err) {
          $('#aiTaskResult').html("Error: " + (err.responseJSON?.error || "Request failed"));
        }
      });
    };
  
    // AI Prioritize Task
    window.aiPrioritize = function(taskId) {
      $('#aiTaskResult').html('<div class="ui active inline loader"></div> AI is prioritizing...').removeClass('hidden');
      $.ajax({
        url: '/ai-prioritize',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ task_id: taskId }),
        success: function(res) {
          $('#aiTaskResult').html("<strong>AI Prioritization:</strong> Task priority set to " + res.task.priority);
          loadTasks();
        },
        error: function(err) {
          $('#aiTaskResult').html("Error: " + (err.responseJSON?.error || "Request failed"));
        }
      });
    };
  
    // AI Suggest Category
    $('#suggestCategoryBtn').click(function() {
      const title = $('#taskTitle').val();
      const desc = $('#taskDesc').val();
      if (!title) {
        alert("Please enter a task title first!");
        return;
      }
      $('#aiTaskResult').html('<div class="ui active inline loader"></div> Suggesting category...').removeClass('hidden');
      $.ajax({
        url: '/ai-suggest-category',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ title: title, desc: desc }),
        success: function(res) {
          $('#taskCategory').val(res.suggested_category);
          $('#aiTaskResult').html("<strong>Category Suggestion:</strong> Based on your task, AI suggests the category: " + res.suggested_category);
        },
        error: function(err) {
          $('#aiTaskResult').html("Error: " + (err.responseJSON?.error || "Request failed"));
        }
      });
    });
  
    // -------------------------------
    // AI Sidebar (hover panel) functions
    // -------------------------------
  
    // When the sidebar's "Ask" button is clicked:
    $('#aiSidebarBtn').click(function() {
      let query = $('#aiSidebarQuery').val().trim();
      if (!query) {
        alert("Please enter a query in the sidebar.");
        return;
      }
      $('#aiSidebarResult')
        .html('<div class="ui active inline loader"></div> Thinking...')
        .removeClass('hidden');
      $.ajax({
        url: '/ai-task',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ query: query }),
        success: function(res) {
          // Show only the AI response in the sidebar
          $('#aiSidebarResult').html("<strong>AI Response:</strong><br>" + res.ai_response);
          // Reveal the "Add Generated Task" button if a response is present
          $('#addGeneratedTaskBtn').removeClass('hidden');
        },
        error: function(err) {
          $('#aiSidebarResult').html("Error: " + (err.responseJSON?.error || "Request failed"));
        }
      });
    });
  
    // When the "Add Generated Task" button is clicked in the sidebar:
    $('#addGeneratedTaskBtn').click(function() {
      // Use the AI response from the sidebar as the task description.
      let generatedDesc = $('#aiSidebarResult').text().replace("AI Response:", "").trim();
      if (!generatedDesc) {
        alert("No generated task to add!");
        return;
      }
      // Here we define a default title for the generated task.
      let generatedTitle = "Generated Task";
      // You can also add logic to extract a title from the response if needed.
      $.ajax({
        url: '/tasks',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
          title: generatedTitle,
          desc: generatedDesc,
          priority: "Medium",
          due_date: "", // Optional: leave blank or set a default due date
          category: "Other",
          status: "Pending"
        }),
        success: function() {
          loadTasks();
          alert("Generated task added!");
          // Optionally clear the sidebar response and query
          $('#aiSidebarQuery').val("");
          $('#aiSidebarResult').addClass('hidden').html("");
          $('#addGeneratedTaskBtn').addClass('hidden');
        },
        error: function(err) {
          alert("Error: " + (err.responseJSON?.error || "Unknown error"));
        }
      });
    });
  });
  