import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AnonymousComponent } from './anonymous.component';

describe('AnonymousComponent', () => {
  let component: AnonymousComponent;
  let fixture: ComponentFixture<AnonymousComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ AnonymousComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AnonymousComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
