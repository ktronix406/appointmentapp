let calendar;
let currentEvent;

document.addEventListener('DOMContentLoaded', function () {
    fetch('/events')
        .then(response => response.json())
        .then(events => {
            const calendarEl = document.getElementById('calendar');
            const calendar = new FullCalendar.Calendar(calendarEl, {
                themeSystem: 'bootstrap',
                initialView: 'dayGridMonth',
                headerToolbar: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay'
                },
                slotMinTime: '08:00:00',
                slotMaxTime: '18:00:00',
                slotDuration: '01:00:00',
                expandRows: true,
                selectable: true,
                selectMirror: true,
                editable: true,
                events: events,  // Use the fetched events

                dateClick(info) {
                    if (calendar.view.type === 'dayGridMonth') {
                        calendar.changeView('timeGridDay', info.dateStr);
                    } else {
                        openCreateModal(info.dateStr);
                    }
                },

                eventClick(info) {
                    openViewModal(info.event);
                },

                eventDrop(info) {
                    confirmMove(info, 'drop');
                },

                eventResize(info) {
                    confirmMove(info, 'resize');
                }
            });

            calendar.render();

            // Re-fetch events when modals are hidden
            document.getElementById('createAppointmentModal').addEventListener('hidden.bs.modal', function () {
                calendar.refetchEvents();
            });

            document.getElementById('editAppointmentModal').addEventListener('hidden.bs.modal', function () {
                calendar.refetchEvents();
            });

            document.getElementById('deleteConfirmationModal').addEventListener('hidden.bs.modal', function () {
                calendar.refetchEvents();
            });
        })
        .catch(error => console.error('Error fetching events:', error));

    // Format date to local ISO
    function formatDateToLocalISO(date) {
        const timezoneOffset = date.getTimezoneOffset() * 60000;
        return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 19);
    }

    // Confirm Move Modal
    function confirmMove(info, actionType) {
        const newStartTime = info.event.start;
        const newEndTime = info.event.end || newStartTime;

        const formattedStartTime = newStartTime.toLocaleString();
        const formattedEndTime = newEndTime.toLocaleString();

        document.getElementById('newDateTime').textContent = `${formattedStartTime} to ${formattedEndTime}`;

        const moveModal = new bootstrap.Modal(document.getElementById('moveConfirmationModal'));
        moveModal.show();

        document.getElementById('confirmMoveButton').onclick = function () {
            moveModal.hide();
            if (actionType === 'drop' || actionType === 'resize') {
                handleEventMoveOrResize(info.event);
            }
        };

        document.getElementById('moveConfirmationModal').addEventListener('hidden.bs.modal', function () {
            calendar.refetchEvents();
        }, { once: true });
    }

    // Handle event move or resize
    function handleEventMoveOrResize(event) {
        const startTimeISO = formatDateToLocalISO(event.start);
        const endTimeISO = event.end ? formatDateToLocalISO(event.end) : startTimeISO;

        fetch(`/appointment/move/${event.id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `start_time=${encodeURIComponent(startTimeISO)}&end_time=${encodeURIComponent(endTimeISO)}`
        }).then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok.');
            }
            return response.json();
        }).then(data => {
            if (data.status !== 'success') {
                alert('Error moving appointment: ' + data.message);
                calendar.refetchEvents();
            }
        }).catch(error => {
            console.error('Fetch error:', error);
            alert('There was an error processing your request.');
            calendar.refetchEvents();
        });
    }

    // Open Edit Modal
    document.getElementById('editAppointmentButton').addEventListener('click', function () {
        const viewModal = bootstrap.Modal.getInstance(document.getElementById('viewAppointmentModal'));
        if (viewModal) {
            viewModal.hide();
        }

        openEditModal(currentEvent);
    });

    // Function to open the Create Modal
    function openCreateModal(dateStr) {
        const modal = new bootstrap.Modal(document.getElementById('createAppointmentModal'));
        document.getElementById('createAppointmentStartTime').value = dateStr;
        document.getElementById('create-appointment-form').reset();
        modal.show();
    }

    // Function to open the View Modal and store the current event
    function openViewModal(event) {
        currentEvent = event; // Store the event data in the global variable

        // Populate and show the View Modal
        const modal = new bootstrap.Modal(document.getElementById('viewAppointmentModal'));
        populateFormWithEventData(event, 'view');
        modal.show();
    }

    // Open Edit Modal with populated data
    function openEditModal(event) {
        const appointmentId = event.id;
        document.getElementById('editAppointmentId').value = appointmentId;

        // Populate the form with event data
        populateFormWithEventData(event, 'edit');

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('editAppointmentModal'));
        modal.show();

        // Handle form submission when the Save button is clicked
        document.getElementById('edit-appointment-form').onsubmit = function (e) {
            e.preventDefault(); // Prevent the default form submission

            const formData = new FormData(this);

            // Create a URL-encoded string manually
            const data = new URLSearchParams();
            data.append('start_time', formData.get('start_time'));
            data.append('duration', formData.get('duration'));
            data.append('vehicle_year', formData.get('vehicle_year'));
            data.append('vehicle_make', formData.get('vehicle_make'));
            data.append('vehicle_model', formData.get('vehicle_model'));
            data.append('installation_type', formData.get('installation_type'));
            data.append('notes', formData.get('notes'));

            formData.getAll('edit_installation_job[]').forEach((job, index) => {
                data.append('edit_installation_job[]', job);
                data.append('edit_installation_price[]', formData.getAll('edit_installation_price[]')[index]);
            });

            formData.getAll('edit_product_name[]').forEach((name, index) => {
                data.append('edit_product_name[]', name);
                data.append('edit_product_price[]', formData.getAll('edit_product_price[]')[index]);
            });

            fetch(`/appointment/edit/${appointmentId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: data.toString()
            })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        modal.hide();

                        // Remove the existing event and add the updated event
                        calendar.getEventById(appointmentId)?.remove();
                        calendar.addEvent({
                            id: appointmentId,
                            title: `${formData.get('customer_first_name')} ${formData.get('vehicle_make')} ${formData.get('vehicle_model')}`,
                            start: formData.get('start_time'),
                            end: new Date(new Date(formData.get('start_time')).getTime() + formData.get('duration') * 3600 * 1000).toISOString(),
                            extendedProps: {
                                customer_first_name: formData.get('customer_first_name'),
                                customer_last_name: formData.get('customer_last_name'),
                                customer_phone: formData.get('customer_phone'),
                                vehicle_year: formData.get('vehicle_year'),
                                vehicle_make: formData.get('vehicle_make'),
                                vehicle_model: formData.get('vehicle_model'),
                                installation_type: formData.get('installation_type'),
                                notes: formData.get('notes'),
                                installation_jobs: formData.getAll('edit_installation_job[]').map((job, index) => ({
                                    job_details: job,
                                    price: formData.getAll('edit_installation_price[]')[index]
                                })),
                                products: formData.getAll('edit_product_name[]').map((name, index) => ({
                                    name: name,
                                    price: formData.getAll('edit_product_price[]')[index]
                                }))
                            }
                        });

                        calendar.changeView('timeGridDay', formData.get('start_time'));
                    } else {
                        alert('Error: ' + result.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('There was an error processing your request.');
                });
        };
    }

    // Populate form fields with event data
    function populateFormWithEventData(event, mode) {
        const prefix = mode === 'edit' ? 'edit' : 'view';

        if (mode === 'view') {
            const startTime = new Date(event.start);
            const endTime = new Date(event.end);

            const formattedStartTime = startTime.toTimeString().slice(0, 5);
            const formattedEndTime = endTime.toTimeString().slice(0, 5);

            document.getElementById('viewAppointmentTime').textContent = `${formattedStartTime} to ${formattedEndTime}`;
        } else if (mode === 'edit') {
            document.getElementById('editAppointmentStartTime').value = formatDateToLocalISO(event.start);
            document.getElementById('editAppointmentId').value = event.id;
        }

        // Populate customer information
        populateField(`${prefix}CustomerFirstName`, event.extendedProps.customer_first_name);
        populateField(`${prefix}CustomerLastName`, event.extendedProps.customer_last_name);
        populateField(`${prefix}CustomerPhone`, event.extendedProps.customer_phone);

        // Populate vehicle information
        populateField(`${prefix}VehicleYear`, event.extendedProps.vehicle_year);
        populateField(`${prefix}VehicleMake`, event.extendedProps.vehicle_make);
        populateField(`${prefix}VehicleModel`, event.extendedProps.vehicle_model);

        // Populate product details
        populateProductDetailsSection(event.extendedProps.products, prefix);

        // Populate installation type and duration
        populateField(`${prefix}InstallationType`, event.extendedProps.installation_type);
        populateField(`${prefix}Duration`, event.extendedProps.duration);
        populateField(`${prefix}Notes`, event.extendedProps.notes);

        // Populate installation jobs
        populateInstallationJobsSection(event.extendedProps.installation_jobs, prefix);
    }

    // Populate input field
    function populateField(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.value = value || '';
        } else {
            console.error(`Element with ID ${elementId} not found`);
        }
    }

    // Populate Product Details Section
    function populateProductDetailsSection(products, prefix) {
        const productSection = document.getElementById(`${prefix}ProductDetailsSection`);

        // Check if the element exists
        if (!productSection) {
            console.error(`Element with ID ${prefix}ProductDetailsSection not found.`);
            return;
        }

        // Check if products is an array and not undefined
        if (!Array.isArray(products)) {
            console.warn('Products is undefined or not an array. Skipping population.');
            productSection.innerHTML = ''; // Optionally clear the section
            return;
        }

        productSection.innerHTML = ''; // Clear any existing product entries

        // Populate product entries
        products.forEach(product => {
            const productEntry = createProductEntry(prefix);
            productEntry.querySelector(`[name="${prefix}_product_name[]"]`).value = product.name || '';
            productEntry.querySelector(`[name="${prefix}_product_price[]"]`).value = product.price || '';
            productSection.appendChild(productEntry);
        });
    }

    // Populate Installation Jobs Section
    function populateInstallationJobsSection(jobs, prefix) {
        const installationJobsSection = document.getElementById(`${prefix}InstallationJobsSection`);
        installationJobsSection.innerHTML = '';

        jobs.forEach(job => {
            const jobEntry = createInstallationJobEntry(job.job_details, job.price, prefix);
            installationJobsSection.appendChild(jobEntry);
        });
    }

    // Create Product Entry for Edit Modal
    function createProductEntry(prefix) {
        const productContainer = document.createElement('div');
        productContainer.className = 'row mb-3 product-entry';

        const productNameDiv = document.createElement('div');
        productNameDiv.className = 'col-md-6';
        const productNameInput = document.createElement('input');
        productNameInput.type = 'text';
        productNameInput.name = `${prefix}_product_name[]`;
        productNameInput.placeholder = 'Enter product name';
        productNameInput.className = 'form-control';
        productNameDiv.appendChild(productNameInput);

        const productPriceDiv = document.createElement('div');
        productPriceDiv.className = 'col-md-6';
        const productPriceInput = document.createElement('input');
        productPriceInput.type = 'text';
        productPriceInput.name = `${prefix}_product_price[]`;
        productPriceInput.placeholder = 'Enter product price (informational only)';
        productPriceInput.className = 'form-control';
        productPriceDiv.appendChild(productPriceInput);

        const removeButtonDiv = document.createElement('div');
        removeButtonDiv.className = 'col-md-12 text-end';
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'btn btn-danger btn-sm remove-product';
        removeButton.textContent = 'Remove Product';
        removeButtonDiv.appendChild(removeButton);

        removeButton.addEventListener('click', function () {
            productContainer.remove();
        });

        productContainer.appendChild(productNameDiv);
        productContainer.appendChild(productPriceDiv);
        productContainer.appendChild(removeButtonDiv);

        return productContainer;
    }

    // Add new product entry for editing
    document.getElementById('addEditProduct').addEventListener('click', function () {
        const productContainer = createProductEntry('edit');
        document.getElementById('editProductDetailsSection').appendChild(productContainer);
    });

    // Add Create Product Entry
    document.getElementById('addCreateProduct').addEventListener('click', function () {
        const productContainer = createProductEntry('create');
        document.getElementById('createProductDetailsSection').appendChild(productContainer);
    });

    // Add Create Installation Job Entry
    document.getElementById('addCreateInstallationJob').addEventListener('click', function () {
        const installationJobEntry = createInstallationJobEntry('', '', 'create');
        document.getElementById('createInstallationJobsSection').appendChild(installationJobEntry);
    });

    // Create Installation Job Entry
    function createInstallationJobEntry(jobDetails, jobPrice, prefix) {
        const jobEntry = document.createElement('div');
        jobEntry.className = 'row mb-3 installation-job-entry';

        const jobDetailsDiv = document.createElement('div');
        jobDetailsDiv.className = 'col-md-6';
        const jobDetailsInput = document.createElement('input');
        jobDetailsInput.type = 'text';
        jobDetailsInput.name = `${prefix}_installation_job[]`;
        jobDetailsInput.value = jobDetails || '';
        jobDetailsInput.placeholder = 'Installation job details';
        jobDetailsInput.className = 'form-control';
        jobDetailsInput.readOnly = (prefix === 'view');
        jobDetailsDiv.appendChild(jobDetailsInput);

        const jobPriceDiv = document.createElement('div');
        jobPriceDiv.className = 'col-md-6';
        const jobPriceInput = document.createElement('input');
        jobPriceInput.type = 'text';
        jobPriceInput.name = `${prefix}_installation_price[]`;
        jobPriceInput.value = jobPrice || '';
        jobPriceInput.placeholder = 'Installation price';
        jobPriceInput.className = 'form-control';
        jobPriceInput.readOnly = (prefix === 'view');
        jobPriceDiv.appendChild(jobPriceInput);

        jobEntry.appendChild(jobDetailsDiv);
        jobEntry.appendChild(jobPriceDiv);

        return jobEntry;
    }

    // Remove Product Entry
    document.querySelectorAll('.remove-product').forEach(button => {
        button.addEventListener('click', function () {
            button.closest('.product-entry').remove();
        });
    });

    // Remove Installation Job Entry
    document.querySelectorAll('.remove-installation-job').forEach(button => {
        button.addEventListener('click', function () {
            button.closest('.installation-job-entry').remove();
        });
    });

    // Confirm Delete Appointment
    document.getElementById('deleteAppointmentButton').addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        const modal = new bootstrap.Modal(document.getElementById('deleteConfirmationModal'));
        modal.show();
    });

    // Handle Delete Confirmation
    document.getElementById('confirmDeleteButton').addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();

        const appointmentId = currentEvent.id;

        fetch(`/appointment/delete/${appointmentId}`, {
            method: 'POST',
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => console.error('Error:', error));
    });
});
